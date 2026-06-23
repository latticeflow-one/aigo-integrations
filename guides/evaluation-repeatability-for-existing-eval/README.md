# Evaluation of Model QA Knowledge

## Overview

This guide shows an example of how to evaluate assess the repeatability of an existing
evaluation, i.e. assess the consistency/stability of the metric values and 
the sample-level scores produced by the task specification in that evaluation. 
In this case, the original tasks specification uses a question-and-answer dataset 
and an LLM as a judge scorer.

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to
be configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal. To use a different model, please adjust the model configuration.

```bash
lf add app -f app.yaml
lf switch playground-app
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run_original_eval.yaml
lf run -f run_repeatability_of_existing_eval.yaml
```
