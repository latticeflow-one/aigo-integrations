# Sample-Dependent Scoring

## Overview

This tutorial shows how to evaluate pre-recorded agent traces with a custom
Python scorer whose checks are driven by **per-sample** evaluation criteria.

The dataset (`datasets/tutorial-samples.jsonl`, 17 tau2bench telecom traces)
stores a recorded `trace` per row together with the rules used to grade it:

- `evaluation_criteria.actions` — tool calls the agent was expected to make.
- `evaluation_criteria.env_assertions` — expected final environment state
  (service status, mobile data, internet speed, MMS capability, etc.).
- `initial_state` — the broken/initialized capabilities the trace started from.

A [`pass_through_solver`](./tasks/task.yaml) replays each recorded trace (no live
model inference happens), and the Python scorer in
[`tasks/scorer.py`](./tasks/scorer.py) reads each sample's criteria at runtime and
applies the matching checks. The final `score` is `min(action_score,
env_assertion_score)` — both components must pass for the sample to succeed.

## Files

| File | Purpose |
| --- | --- |
| `app.yaml` | Project definition. |
| `run.yaml` | Wires the model, dataset, and task into an evaluation. |
| `tasks/task.yaml` | Task spec: pass-through solver + Python scorer and metrics. |
| `tasks/scorer.py` | The sample-dependent scoring logic. |
| `datasets/tutorial-samples.yaml` | Dataset spec pointing at the JSONL. |
| `datasets/tutorial-samples.jsonl` | 17 recorded traces with per-sample criteria. |

## Setup

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

The `OPENAI_API_KEY` is required only because the platform needs a registered
model — no actual inference is performed; the pass-through solver reads the
pre-recorded traces from the dataset.

## Usage

```bash
lf add app -f app.yaml
lf switch tutorial-tau2bench
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run run.yaml
```

The evaluation reports four metrics: **Task Score**, **Action Score**,
**Env Assertion Score**, and **Action Coverage**.
