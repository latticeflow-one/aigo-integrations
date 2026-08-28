# OpenAI Chat Completion Model with Secrets

## Overview

This guide shows an example integration of OpenAI GPT-4.1 Nano model using the secrets
to hide the sensitive API key.

The model uses the default chat completion API
[endpoint](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI API key by
creating a `.env` file.

```dotenv
OPENAI_API_KEY=<OPENAI_API_KEY>
```

```bash
lf add model -f models/openai_gpt_4-1-nano.yaml
lf test model openai-gpt-4-1-nano
```
