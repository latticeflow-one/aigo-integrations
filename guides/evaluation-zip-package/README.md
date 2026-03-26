# Evaluation Zip Package

## Overview

This guide shows an example of initializing, configuring, and running an evaluation using a ZIP package from URL.

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to
be configured as an environment variable `OPENAI_API_KEY` in the
terminal. To use a different model, please adjust the model configuration.

```bash
lf app add -f app.yaml
lf switch evaluation-zip-package-app
lf model add -f model.yaml
lf init --url
lf run -f run.yaml
```
