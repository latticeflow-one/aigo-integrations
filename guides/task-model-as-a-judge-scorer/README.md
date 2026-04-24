# Model As A Judge Scorer

## Overview

This guide shows an example of a task that uses the model-as-a-judge scorer to
evaluate model responses on a retrieval-augmented generation (RAG) task.

The scorer uses a separate judge model to assign a numeric score between 0 and 100
based on a configurable evaluation dimension (e.g. groundedness or relevance). The
judge model and the evaluation dimension are both exposed as config parameters, so
the same task can be run with different judges or assessed across multiple dimensions
in a single evaluation.

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to
be configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal. To use a different model, please adjust the model configuration.

```bash
lf add app -f app.yaml
lf switch playground-app
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

If you want to iterate on the task definition, try:

```bash
lf test task -f run.yaml -sk rag-qa-groundedness-gpt-4-1-nano -n 1
```
