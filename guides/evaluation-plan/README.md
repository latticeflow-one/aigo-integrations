# Evaluation Plan

## Overview

This guide shows how to bundle several evaluation runs into a single evaluation plan
and run them together. The plan reuses one Harry Potter trivia task and dataset and
compares two OpenAI models - GPT-4.1 Nano and GPT-4.1 Mini - each judged by an 
LLM-as-a-judge scorer. Every entry under `evaluations` is a complete run config, so
the same file creates all dependencies and starts one evaluation per entry, grouped
under one plan run. The plan shows both ways to declare an entry: the first is written
inline, and the second is pulled in from its own file (`evaluations/hp_trivia.yaml`)
with `$ref`, so that run config can also be reused and run on its own with 
`lf run -f ./evaluations/hp_trivia.yaml`.

## Usage

This guide uses OpenAI models as an example. It requires the OpenAI integration to be
configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal. To compare different models, adjust the model keys in `eval-plan.yaml`.

```bash
lf add app -f app.yaml
lf switch evaluation-plan
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f eval-plan.yaml
```

`lf run` starts every evaluation run in the plan and prints the command to inspect it.
Track the plan run and its per-evaluation metrics with:

```bash
lf list eval-plan
lf overview eval-plan --id <plan-run-id>
```
