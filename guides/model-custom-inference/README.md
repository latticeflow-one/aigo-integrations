# Model with Custom Inference

## Overview

This guide shows an example integration of a model with custom inference logic.

The custom logic is implemented as a Python code snippet and uses OpenAI's GPT-4.1
as an example.

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI API key by
creating a `.env` file.

```bash
OPENAI_API_KEY=<OPENAI_API_KEY>
```

```bash
lf add model -f models/model.yaml
lf test model gpt-4-1-nano-custom-inference
```
