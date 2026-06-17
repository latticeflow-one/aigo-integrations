# Risk Policies

## Overview

This guide shows how to configure a **risk scorer** and attach **risk policies** to an
AI app so that evaluation metrics are translated into risk scores and surfaced in the AI app
risk dashboard.

A **risk scorer** is a reusable function that converts a raw evaluation metric (e.g.
`accuracy`) into a normalized risk score. A **risk policy** binds a risk scorer to a
specific set of in-scope evaluations and metrics, and configures the risk scorer's
parameters.

Each policy score is assigned a severity level based on the computed value:

| Level | Score range |
|-------|-------------|
| `low` | 0 – 2.0 |
| `medium` | 2.0 – 4.0 |
| `high` | 4.0 – 9.0 |
| `critical` | above 9.0 |

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to
be configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal.

```bash
lf add app -f app.yaml
lf switch playground-app
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf add risk-scorer -f risk_scorer.yaml
lf set risk-policies -f risk_policies.yaml
lf run -f run.yaml
lf overview risk-policies
```

To inspect a single policy:

```bash
lf overview risk-policies --key quality_external
```

## Files

### `run.yaml`

Runs a small AI knowledge multiple-choice evaluation that produces an `accuracy` metric.
The evaluation key `qa_evaluation` matches the finegrained scope of the `quality` risk
policy, so the policy picks up its score immediately after the run completes.

### `risk_scorer.yaml`

Defines the scoring formula and its configurable parameters. The scorer in this guide
converts an `accuracy` metric into a risk score by inverting it and scaling by
configurable impact and deployment reach factors:

```
score = (1 − accuracy) × impact × deployment_reach
```

The `metric_key` field names the variable in `function` that receives the live metric
value from the evaluation. All other variables must be covered by `config_spec` entries.

```yaml
key: "performance_risk_scorer"
function: "(1 - accuracy) * impact * deployment_reach"
metric_key: "accuracy"
config_spec:
  - type: float
    key: "impact"
    default_value: 5.0
    min: 0.0
    max: 10.0
  - type: categorical
    key: "deployment_reach"
    allowed_values: ["internal", "external"]
    default_value: "external"
    values_mapping:
      internal: 0.5
      external: 1.0
```

A single scorer can be shared across many policies. Each policy supplies its own
`config` values when referencing the scorer.

### `risk_policies.yaml`

Each risk policy:

- References a scorer by `risk_scorer_key`.
- Targets evaluations via `scope` — either `all_latest` (all evaluation keys, latest
  run each) or a finegrained list of specific evaluation keys.
- Selects the metric to feed into the risk scorer via `metric`.
- Provides risk scorer config spec values in `config`.

```yaml
policies:
  - key: "quality_internal"
    display_name: "Quality Risk Policy (Internal)"
    domain: "quality"
    risk_scorer_key: "performance_risk_scorer"
    scope:
      evaluation_keys: ["qa_evaluation"]
    metric: "accuracy"
    aggregation: "mean"
    config:
      impact: 4.0
      deployment_reach: "internal"

  - key: "quality_external"
    display_name: "Quality Risk Policy (External)"
    domain: "quality"
    risk_scorer_key: "performance_risk_scorer"
    scope:
      evaluation_keys: ["qa_evaluation"]
    metric: "accuracy"
    aggregation: "mean"
    config:
      impact: 4.0
      deployment_reach: "external"
```

`lf set risk-policies` **replaces** the full set of policies atomically. To remove a policy, omit it from the file and re-run `lf set risk-policies`.
