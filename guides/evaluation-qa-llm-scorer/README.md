# Evaluation of Model QA Knowledge

## Overview

This guide shows an example of how to evaluate the knowledge of a model on a specific
topic. The evaluation uses a question-and-answer dataset and an LLM as a judge scorer.

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

If you want to iterate on the task definition or specification, try:

```bash
lf test task -f run.yaml -sk hp-trivia-gpt-4-1-nano --num-samples 1
```
