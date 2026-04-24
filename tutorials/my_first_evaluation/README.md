# My First Evaluation

## Overview

This is an example for running your first evaluation in AI GO!. We will run the
AILuminate hate benchmark on a OpenAI model.

## Usage

```bash
lf add app -f app.yaml
lf switch my-first-eval
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run run.yaml
```
