# Model with Streaming Response

## Overview

This guide shows an example integration of a model with a (SSE) streaming response.

It uses OpenAI's model as an example. Learn more about streaming responses in OpenAI's
[documentation](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI API key by
creating a `.env` file.

```dotenv
OPENAI_API_KEY=<OPENAI_API_KEY>
```

```bash
lf add -f run.yaml
lf test model openai-gpt-4-1-nano
```
