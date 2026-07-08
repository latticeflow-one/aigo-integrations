# String Equals MCQA Scorer

## Overview

This guide shows an example of a task that uses the string equals MCQA scorer to
evaluate multiple choice question answering tasks.

The scorer compares the model's single-character response to the correct answer
choice from the dataset. The answer column is configurable via a `dataset_column`
config parameter, allowing the same task definition to be reused across datasets
with different column naming conventions.

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to
be configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal. To use a different model, please adjust the model configuration.

```bash
lf add app -f app.yaml
lf switch task-string-equals-mcqa-scorer
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

If you want to iterate on the task definition, try:

```bash
lf test task -f run.yaml -sk mcqa-gpt-4-1-nano -n 1
```
