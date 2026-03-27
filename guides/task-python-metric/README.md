# Python Metric

## Overview

This guide shows an example of a task that uses a Python scorer paired with a Python
metric for fully custom evaluation logic.

The Python scorer (`compute_scores`) runs once per sample and returns a dictionary of
per-sample values. The Python metric (`compute_metrics`) then aggregates all sample
scores and returns a dictionary of named metric values. This combination is useful
when the built-in metric types (mean, min, max) are insufficient for the aggregation
logic required.

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to
be configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal. To use a different model, please adjust the model configuration.

```bash
lf app add -f app.yaml
lf switch playground-app
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

If you want to iterate on the task definition, try:

```bash
lf test task -f run.yaml -sk geography-qa-gpt-4-1-nano -n 1
```
