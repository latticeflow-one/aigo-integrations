# Evaluation Plan

## Overview

This guide shows how to bundle several evaluations into a single evaluation plan
and run them together, creating an evaluation plan run. The plan reuses one
Harry Potter trivia evaluation and compares two OpenAI models - GPT-4.1 Nano and
GPT-4.1 Mini - each judged by an LLM-as-a-judge scorer. Every entry under
`evaluation_specifications` sets which evaluation is run and what is the config it
is run with. Mind that the evaluation, together with all of its dependencies, has to
exist before the evaluation plan is created.

## Usage

This guide uses OpenAI models as an example. It requires the OpenAI integration to be
configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal. To compare different models, adjust the model keys in `eval-plan.yaml`.

```bash
lf add app -f app.yaml
lf switch evaluation-plan
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf add -f run.yaml
lf run eval-plan -f eval-plan.yaml
```

`lf run eval-plan` starts every evaluation run in the evaluation plan. Track the
evaluation plan run and its evaluation runs with:

```bash
lf overview eval-plan-run --id <eval-plan-run-id>
```
