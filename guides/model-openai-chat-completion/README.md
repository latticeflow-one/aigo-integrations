# OpenAI GPT-4.1 Nano

## Overview

This guide shows an example integration of OpenAI GPT-4.1 Nano model without the use of
any built-in models or model adapters.

The model uses the default chat completion API
[endpoint](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI API key by
creating a `.env` file.

```bash
OPENAI_API_KEY=<OPENAI_API_KEY>
```

```bash
lf app add -f app.yaml
lf switch playground-app
lf add -f run.yaml
lf test model openai-gpt-4-1-nano
```
