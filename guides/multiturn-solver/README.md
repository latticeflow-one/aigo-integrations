# Multi-turn Task

## Overview

This guide shows an example of a multi-turn evaluation task.

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to 
be configured either in the UI or as an environment variable `OPENAI_API_KEY` in the
terminal. To use a different model, please adjust the model configuration.

```bash
lf app add -f app.yaml
lf switch playground-app
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```
