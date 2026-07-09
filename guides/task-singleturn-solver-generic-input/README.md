# Single-turn Task with Generic Input Builder

## Overview

This guide shows an example of a task that uses a single-turn solver with generic
input builder.

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to
be configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal. To use a different model, please adjust the model configuration.

```bash
lf add app -f app.yaml
lf switch task-singleturn-solver-generic-input
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

If you want to iterate on the task definition, try:

```bash
lf test task -f run.yaml -sk singleturn-generic-input-gpt-4-1-nano -n 1
```
