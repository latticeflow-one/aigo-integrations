# Task with Model As A Judge Scoring

## Overview

This guide shows how to score model outputs with a **model-as-a-judge** — a
separate judge model that grades responses. It covers two levels:

- **Basic** (`tasks/qa_basic.yaml`): single-turn QA graded two ways on the same
  answer — a `model_as_a_judge_classifier` for correctness (correct/incorrect)
  and a `model_as_a_judge_scorer` for a numeric quality score (0–100).
- **Advanced** (`tasks/conversation_advanced.yaml`): a two-turn conversation
  graded as a whole. The judge prompt renders the **entire conversation** (not
  just the last reply), assigns one of four rubric labels with
  `labeler_via_model`, turns labels into a single score with a `weighted_average`
  metric, and reports the label distribution with `frequency`.

The full walkthrough is in `model-as-a-judge-scoring.mdx`.

## Usage

This guide uses an OpenAI model as both the evaluated model and the judge. It
requires the OpenAI integration to be configured either in the UI or as an
environment variable `OPENAI_API_KEY` in the terminal. To use a different model,
adjust the model configuration.

```bash
lf add app -f app.yaml
lf switch task-model-as-a-judge
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

If you want to iterate on a task definition, try:

```bash
lf test task -f run.yaml -sk judge-qa-basic-gpt-4-1-nano -n 1
lf test task -f run.yaml -sk judge-conversation-advanced-gpt-4-1-nano -n 1
```
