# Model As A Judge Scorer

## Overview

This guide shows an example of the trials in order to assess model reliability.

Each sample is run multiple times and each solver output is scored. The scores for
each of these trials are then aggregated into a reliability score (`pass^3`) that
estimates the probability that if the model is run 3 times, it would succeed in all 3
trials.

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
