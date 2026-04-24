# Python Solver

## Overview

This guide shows an example of a task that uses a Python solver to manage the
conversation trace programmatically.

Unlike the declarative solver types, the Python solver gives full control over how
the conversation is constructed and how the model is called. The `run_solver` function
receives the dataset sample, the model, and the current trace, and returns the updated
trace after the model responds.

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
lf test task -f run.yaml -sk geography-qa-gpt-4-1-nano -n 1
```
