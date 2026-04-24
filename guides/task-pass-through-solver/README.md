# Pass-through Solver

## Overview

This guide shows an example of a pass-through evaluation task.

The pass-through solver (`pass_through_solver`) does **not** call any model.
Instead, it reads a pre-recorded conversation trace directly from a dataset
column and passes it to the scorers as-is. This makes it ideal for evaluating
conversations that have already been collected — for example, from production
logs or offline agent runs — without re-running any model.

Each record in the dataset contains:

- `trace` — a pre-recorded conversation stored in the Open Responses trace
  format (a JSON object with an `items` array of messages, function calls, and
  function call outputs).
- `target` — the expected answer used by the `string_equals` scorer.

## Usage

Although the pass-through solver never calls any model, the platform requires a
model to be registered as part of the evaluation. This guide uses an OpenAI model
as a placeholder. It requires the OpenAI integration to be configured either in
the UI or as an environment variable `OPENAI_API_KEY` in the terminal. To use a
different model, please adjust the model configuration.

```bash
lf add app -f app.yaml
lf switch playground-app
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

If you want to iterate on the task definition, try:

```bash
lf test task -f run.yaml -sk pass-through-qa
```

## How It Works

The task specification in `tasks/pass_through.yaml` configures the solver as:

```yaml
solver:
  type: "pass_through_solver"
  message_format: "open_responses"
  trace_column: "trace"
```

For each dataset sample the solver reads `sample["trace"]`, deserializes it as
a `Trace` object, and produces a solver output that the scorers can consume —
all without making any model call.

The dataset in `datasets/recorded_qa_traces.jsonl` contains a mix of traces.
Simple records are single-turn Q&A exchanges:

```json
{
  "target": "Tokyo",
  "trace": {
    "FORMAT": "open_responses",
    "items": [
      {"type": "message", "id": "", "status": "completed", "role": "system",
       "content": [{"type": "input_text", "text": "You are a helpful assistant. Answer concisely with a single word."}]},
      {"type": "message", "id": "", "status": "completed", "role": "user",
       "content": [{"type": "input_text", "text": "What is the capital city of Japan?"}]},
      {"type": "message", "id": "", "status": "completed", "role": "assistant",
       "content": [{"type": "output_text", "text": "Tokyo", "annotations": [], "logprobs": null}]}
    ]
  }
}
```

One record demonstrates a multi-turn conversation where the model uses a
`get_current_weather` tool across two user turns:

```json
{
  "target": "In Berlin it is currently 4°C and overcast.",
  "trace": {
    "FORMAT": "open_responses",
    "items": [
      {"type": "message", "id": "", "status": "completed", "role": "system",
       "content": [{"type": "input_text", "text": "You are a helpful assistant with access to weather tools."}]},
      {"type": "message", "id": "", "status": "completed", "role": "user",
       "content": [{"type": "input_text", "text": "What is the current temperature in Seoul?"}]},
      {"type": "function_call", "id": "", "call_id": "c1", "name": "get_current_weather",
       "arguments": "{\"city\": \"Seoul\", \"unit\": \"celsius\"}", "status": "completed"},
      {"type": "function_call_output", "id": "", "call_id": "c1",
       "output": "{\"temperature\": 11, \"condition\": \"partly cloudy\"}", "status": "completed"},
      {"type": "message", "id": "", "status": "completed", "role": "assistant",
       "content": [{"type": "output_text", "text": "The current temperature in Seoul is 11°C with partly cloudy skies.", "annotations": [], "logprobs": null}]},
      {"type": "message", "id": "", "status": "completed", "role": "user",
       "content": [{"type": "input_text", "text": "And what about Berlin?"}]},
      {"type": "function_call", "id": "", "call_id": "c2", "name": "get_current_weather",
       "arguments": "{\"city\": \"Berlin\", \"unit\": \"celsius\"}", "status": "completed"},
      {"type": "function_call_output", "id": "", "call_id": "c2",
       "output": "{\"temperature\": 4, \"condition\": \"overcast\"}", "status": "completed"},
      {"type": "message", "id": "", "status": "completed", "role": "assistant",
       "content": [{"type": "output_text", "text": "In Berlin it is currently 4°C and overcast.", "annotations": [], "logprobs": null}]}
    ]
  }
}
```

## Message Format

The `pass_through_solver` supports an optional `message_format` field, note that in order to parse function call and outputs, you must use `open_responses` format:

| Value | Description |
|---|---|
| `latticeflow` (default) | Converts the trace to `LFMessage` objects. Compatible with standard scorers such as `string_equals` and `model_as_a_judge`. |
| `open_responses` | Preserves the full structured trace including function calls and function call outputs. Required for trace-aware scorers such as `FunctionCallCoverage`. |
