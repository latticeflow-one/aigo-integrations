# Sample-Dependent Scoring for Agent Traces

This tutorial demonstrates how to evaluate pre-recorded agent traces where **each sample defines its own evaluation rules**. Instead of applying one fixed scoring rubric to every sample, the scorer reads per-sample assertion rules from the dataset and applies them dynamically at runtime.

This pattern appears in many agent benchmarks -- tau-bench, SWE-bench, GAIA, and others -- where each task has unique success criteria defined alongside the data.

## What you will build

A complete AI GO! evaluation that:

1. Reads pre-recorded multi-turn agent traces (no live model needed)
2. Scores each trace against its own evaluation criteria
3. Combines multiple scoring components into a final score

The evaluation uses the **tau2bench telecom benchmark** -- 17 curated samples of LLM agents handling customer service scenarios like airplane mode troubleshooting, overdue bill resolution, and MMS configuration.

By the end, you will have a working evaluation you can adapt to any benchmark that embeds per-sample evaluation rules in its dataset.

---

## Step 1: Understand the data

Each sample in the dataset represents one agent conversation and carries its own evaluation rules. Here is the schema:

```json
{
  "task_id": "[service_issue]airplane_mode_on|break_apn_settings|...",
  "trace": { ... },
  "evaluation_criteria": {
    "actions": [ ... ],
    "env_assertions": [ ... ]
  },
  "initial_state": {
    "initialization_actions": [ ... ]
  }
}
```

The key insight is that `evaluation_criteria` varies per sample. Some samples require checking 1 environment assertion; others require checking 3 assertions plus a set of expected tool calls. The scorer must adapt to whatever each sample demands.

### The trace

The `trace` field contains a multi-turn conversation in AI GO! trace format. Trace items interleave three types:

| Type | Description |
|------|-------------|
| `message` | Text messages (role: `user` or `assistant`) |
| `function_call` | A tool invocation with `name`, `arguments`, and `created_by` |
| `function_call_output` | The result of a tool call, linked by `call_id` |

Here is a simplified view of a typical trace:

```
[0] assistant: "Hi! How can I help you today?"
[1] user:      "My phone is showing No Service..."
[2] function_call: get_customer_by_phone (created_by: assistant)
[3] function_call_output: {"customer_id": "C1001", ...}
[4] function_call: get_details_by_id (created_by: assistant)
[5] function_call_output: {"line_id": "L1002", "status": "Suspended", ...}
[6] assistant: "I see the issue — your line is suspended due to an overdue bill..."
[7] function_call: make_payment (created_by: user)
[8] function_call_output: {"success": true}
    ...
```

Both `user` and `assistant` can issue function calls. User-side calls are device operations (toggling airplane mode, rebooting). Assistant-side calls are backend operations (looking up accounts, enabling roaming).

### Evaluation criteria

Each sample defines two types of checks:

**Action checks** list the tool calls that should appear in the trace:

```json
"actions": [
  { "name": "transfer_to_human_agents", "requestor": "assistant" }
]
```

**Environment assertions** define the expected final state of the environment:

```json
"env_assertions": [
  {
    "func_name": "assert_service_status",
    "arguments": { "expected_status": "connected" },
    "assert_value": true
  },
  {
    "func_name": "assert_no_overdue_bill",
    "arguments": { "overdue_bill_id": "B1234321" },
    "assert_value": true
  }
]
```

Both components must pass for a sample to succeed -- the final score is `min(action_score, env_assertion_score)`.

### Examples

A simple transfer scenario only needs 1 action + 1 env assertion:

```yaml
actions:
  - name: transfer_to_human_agents
    requestor: assistant
env_assertions:
  - func_name: assert_service_status
    arguments: { expected_status: no_service }
```

A complex resolution scenario checks 7 actions + 2 env assertions:

```yaml
actions:
  - { name: toggle_airplane_mode, requestor: user }
  - { name: reset_apn_settings, requestor: user }
  - { name: make_payment, requestor: user }
  # ... 4 more expected actions
env_assertions:
  - func_name: assert_service_status
    arguments: { expected_status: connected }
  - func_name: assert_no_overdue_bill
    arguments: { overdue_bill_id: B1234321 }
```

The scorer reads these structures at runtime and applies exactly the checks each sample requires -- no hardcoded logic for specific scenarios.

---

## Step 2: Build the scorer

The scorer is a Python file that defines a `compute_scores` function. AI GO! calls it once per sample, passing the dataset row and the solver output.

We organize all scoring logic in a `TraceScorer` class. The constructor parses the trace once, and assertion handlers access that shared state via `self`:

```python
class TraceScorer:

    def __init__(self, trace, init_actions):
        self.trace = trace
        self.calls = self.extract_calls()
        self.status_bar = self.find_last_status_bar()
        self.broken = {a["func_name"] for a in init_actions}
```

`self.calls` holds the extracted function calls, `self.status_bar` is the last Status Bar text from the trace, and `self.broken` tracks which device capabilities were deliberately broken during scenario setup. All assertion handlers can access these without extra arguments.

### Extract function calls from the trace

```python
def extract_calls(self):
    outputs = {}
    for item in self.trace.items:
        if item.type == "function_call_output":
            outputs[item.call_id] = (
                item.output if isinstance(item.output, str) else str(item.output)
            )

    calls = []
    for item in self.trace.items:
        if item.type == "function_call":
            args = json.loads(item.arguments) if item.arguments else {}
            calls.append({
                "name": item.name,
                "args": args,
                "created_by": item.created_by,
                "output": outputs.get(item.call_id),
            })
    return calls
```

This walks the trace items in two passes: first collecting outputs by `call_id`, then pairing them with their function calls.

### Action checks

Action checks answer: *"Did the agent perform this specific tool call?"*

```python
def check_actions(self, expected):
    return [
        any(
            c["name"] == action["name"] and c["created_by"] == action["requestor"]
            for c in self.calls
        )
        for action in expected
    ]
```

Each expected action specifies a `name` and `requestor` (who should have made the call: `"user"` or `"assistant"`). The check is a simple presence test -- if the call exists anywhere in the trace, it passes.

### Environment assertion dispatch

Environment assertions answer: *"Is the environment in the expected state?"* Each assertion type requires different logic. The `func_name` in the data maps directly to a method on the class, so dispatch is just a `getattr` call:

```python
def check_env_assertions(self, assertions):
    results = []
    for assertion in assertions:
        handler = getattr(self, assertion["func_name"], None)
        if handler is None:
            results.append(False)
            continue
        met = handler(assertion.get("arguments", {}))
        results.append(met == assertion.get("assert_value", True))
    return results
```

Adding a new assertion type means adding a method whose name matches the `func_name` in the data. No registration step needed.

### Assertion handlers

Each handler inspects trace data in a different way. Here are three examples that illustrate the range of patterns:

**Pattern 1 -- Check a tool output for a text pattern:**

```python
def assert_service_status(self, expected):
    status = expected["expected_status"]
    if self.status_bar is not None:
        has_signal = "📶" in self.status_bar
        no_signal = "📵" in self.status_bar or "✈" in self.status_bar
        if status == "connected":
            return has_signal and not no_signal
        return no_signal or not has_signal
    # Fallback: if agent transferred, service was never fixed
    transferred = any(c["name"] == "transfer_to_human_agents" for c in self.calls)
    return (not transferred) if status == "connected" else True
```

This reads the last Status Bar from the trace's tool outputs and checks for signal indicators. Notice how `self.status_bar` and `self.calls` are already available -- no need to pass them as arguments.

**Pattern 2 -- Cross-reference initial state with trace actions:**

```python
def assert_no_overdue_bill(self, expected):
    if "suspend_line_for_overdue_bill" not in self.broken:
        return True   # bill was never overdue
    return any(c["name"] == "make_payment" for c in self.calls)
```

This checks whether a bill was made overdue in the scenario setup (`self.broken`), and if so, whether the agent guided the user to make a payment.

**Pattern 3 -- Match specific tool call arguments:**

```python
def assert_data_refueling_amount(self, expected):
    return any(
        c["name"] == "refuel_data"
        and c["args"].get("customer_id") == expected["customer_id"]
        and c["args"].get("line_id") == expected["line_id"]
        and c["args"].get("gb_amount") == expected["expected_amount"]
        for c in self.calls
    )
```

This verifies that the agent called `refuel_data` with exactly the right customer, line, and amount.

### Combine into the final score

The `score` method ties both components together:

```python
def score(self, criteria):
    action_results = self.check_actions(criteria.get("actions", []))
    action_score = 1.0 if all(action_results) else 0.0 if action_results else 1.0
    action_coverage = sum(action_results) / len(action_results) if action_results else 1.0

    env_results = self.check_env_assertions(criteria.get("env_assertions", []))
    env_score = 1.0 if all(env_results) else 0.0 if env_results else 1.0

    return {
        "score": min(action_score, env_score),
        "action_score": action_score,
        "env_assertion_score": env_score,
        "action_coverage": action_coverage,
    }
```

### The entry point

The `compute_scores` function instantiates the class and delegates:

```python
def compute_scores(sample, solver_output):
    scorer = TraceScorer(solver_output.trace, sample["initial_state"]["initialization_actions"])
    return scorer.score(sample["evaluation_criteria"])
```

The scorer returns a dict of fields. AI GO! stores these per-sample and aggregates them into metrics defined in the task YAML.

---

## Step 3: Wire up the task

The task YAML connects the solver, scorer, and metrics.

### Pass-through solver

Since we are evaluating pre-recorded traces (not calling a live model), we use a **pass-through solver**. It reads a trace directly from the dataset sample and passes it to the scorer without making any model calls:

```yaml
solver:
  type: pass_through_solver
  trace_column: "trace"
  message_format: "open_responses"
```

- `trace_column` points to the dataset field containing the trace
- `message_format: "open_responses"` tells the platform the trace uses the AI GO! trace format

### Python scorer with metrics

The scorer is attached to the task with metrics that aggregate per-sample scores into evaluation-level results:

```yaml
scorers:
  - type: python
    compute_scores_snippet: !include "./scorer.py"
    metrics:
      - type: mean
        field: score
        name: "Task Score"
      - type: mean
        key: action_score_mean
        field: action_score
        name: "Action Score"
      - type: mean
        key: env_assertion_score_mean
        field: env_assertion_score
        name: "Env Assertion Score"
      - type: mean
        key: action_coverage_mean
        field: action_coverage
        name: "Action Coverage"
```

Each metric computes the `mean` of a scorer output field across all samples. The `key` field ensures unique metric identifiers when multiple metrics share the same `type`.

### Reusable task via config_spec

To make the task reusable across different datasets without modifying the YAML, we declare a `config_spec` parameter:

```yaml
config_spec:
  - type: dataset
    key: eval_dataset
    display_name: Evaluation Dataset

definition:
  dataset:
    key: "<< config.eval_dataset >>"
```

The `<< config.eval_dataset >>` placeholder is resolved at evaluation time from the `task_config` in the run YAML.

---

## Step 4: Run the evaluation

### Setup

```bash
# Create and switch to the AI App
lf add app -f app.yaml
lf switch tutorial-tau2bench

# Copy .env.example to .env and fill in your OpenAI API key
cp .env.example .env
# edit .env

# Validate the configuration
lf run -f run.yaml -v
```

### Run

```bash
# Upload entities and run the evaluation
lf run -f run.yaml -w
```

The `-w` flag waits for the evaluation to finish. With 17 samples and no model calls, it completes in under a minute.

### Results

```
Task Score:               0.53
Action Score:             0.53
Env Assertion Score:      0.71
Action Coverage:          0.66
```

- **Task Score** (0.53): 9 of 17 samples passed all checks
- **Env Assertion Score** (0.71): higher than the overall score because some samples pass their env assertions but fail on action checks
- **Action Coverage** (0.66): on average, 66% of expected tool calls were found in the traces -- useful for diagnosing partial failures

### Inspecting per-sample results

In the AI GO! UI, you can filter and sort samples by any scorer output field. Sort by `action_coverage` to see which samples had partial action matches, or filter by `score = 0` to focus on failures.

---

## Adapting this pattern

The sample-dependent scoring pattern generalizes to any evaluation where samples carry their own success criteria.

### Adding new assertion types

Just add a method to `TraceScorer` whose name matches the `func_name` in the data:

```python
class TraceScorer:
    ...

    def assert_new_check(self, expected):
        # Your evaluation logic using self.calls, self.status_bar, etc.
        return True or False
```

No registration or dispatch table needed -- `check_env_assertions` resolves the method by name automatically.

### Evaluating multiple models

Use `config_spec` with a `dataset` parameter to point the same task at different datasets. In the run YAML, add one `task_specification` per model:

```yaml
evaluation:
  task_specifications:
    - task_key: tau2bench-tutorial-eval
      model_key: "openai$gpt-4-1-nano"
      task_config:
        eval_dataset: model-a-traces
    - task_key: tau2bench-tutorial-eval
      model_key: "openai$gpt-4-1-nano"
      task_config:
        eval_dataset: model-b-traces
```

### Converting your own benchmark traces

To adapt this for a different benchmark:

1. **Convert traces** to the AI GO! trace format (items with `message`, `function_call`, `function_call_output` types)
2. **Embed evaluation criteria** in each dataset sample -- whatever fields your scorer needs to know what to check
3. **Extend `TraceScorer`** with assertion handlers that extract signals from the trace and compare against the per-sample criteria
4. **Name each handler** to match the `func_name` in the data -- dispatch happens automatically

The scorer's structure -- parse trace once, dispatch by assertion type, combine components -- stays the same regardless of the benchmark domain.
