# Evaluation of Model QA Knowledge

## Overview

This guide shows an example of how to assess the repeatability of a task specification,
i.e. the consistency/stability of the metric values and sample-level scores it produces.
In this case, the original task specification uses a question-and-answer dataset and an
LLM as a judge scorer.

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
