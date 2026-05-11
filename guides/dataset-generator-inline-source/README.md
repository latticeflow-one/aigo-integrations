# Dataset Generator with LLM Synthesizer

## Overview

This guide shows an example of a dataset generator that uses an inline samples source
and an LLM as a synthesizer. The dataset generator is then used to generate a sample
dataset.

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

If you want to iterate on the dataset generation, try:

```bash
lf test dataset -f run.yaml --key science-questions-dataset --num-samples 10
```
