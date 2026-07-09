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
lf switch risk-policies
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
