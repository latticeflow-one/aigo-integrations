# Dataset Generator with Python Synthesizer and Secrets

## Overview

This guide shows an example of a dataset generator that uses a Python script as the
synthesizer. The dataset generator uses secrets to hide sensitive information such as API keys. Secrets can be reused in multiple places in the synthesizer script. The dataset generator is then used to generate a sample dataset of Harry Potter questions using an OpenAI model.

It showcases how to generate sample questions without any seed dataset, how to use
standard Python libraries and how to use secrets in Python synthesizer snippets.

## Usage

This guide uses an OpenAI model as an example in the Python synthesizer snippet to generate questions. Configure the OpenAI API key by creating a .env file.

```bash
OPENAI_API_KEY=<OPENAI_API_KEY>
```

```bash
lf add app -f app.yaml
lf switch dataset-generator-synthesizer-secrets
lf add -f run.yaml
```

If you want to iterate on the dataset generation, try:

```bash
lf test dataset -f run.yaml --key dataset-python-synthesizer-secrets --num-samples 4
```
