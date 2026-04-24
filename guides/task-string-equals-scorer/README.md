# String Equals Scorer

## Overview

This guide shows an example of a task that uses the string equals scorer to evaluate
model responses against both a fixed and a dynamic ground truth value.

The task evaluates yes/no questions with a string equals scorer that checks model
responses against the correct answer from the dataset. It also demonstrates
`int` and `boolean` config parameters to control response length and context inclusion.

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
lf test task -f run.yaml -sk yes-no-qa-gpt-4-1-nano -n 1
```
