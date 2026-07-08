# Multi-turn task with a Loop

## Overview

This guide shows an example of a multi-turn task that uses the `loop` message builder
to run a repeated exchange between a judge model and the evaluated model.

The evaluated model is instructed to ask for confirmation before answering. The loop
runs up to three iterations: on each iteration a `generate_message` step uses a
separate judge model to reply to any clarifying question, and a `generate` step
produces the next model response. The loop terminates as soon as the judge replies
with `<done>`, indicating the conversation is complete.

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to
be configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal. To use a different model, please adjust the model configuration.

```bash
lf add app -f app.yaml
lf switch task-generate-loop
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

If you want to iterate on the task definition, try:

```bash
lf test task -f run.yaml -sk generate-loop-gpt-4-1-nano -n 1
```
