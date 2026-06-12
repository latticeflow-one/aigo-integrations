# Azure OpenAI Models

## Overview

This guide shows Azure OpenAI integration patterns for both the Chat Completions
and Responses APIs using the Bearer token authentication.

## Usage

Configure the endpoint and the API key by creating a `.env` file.

```text
AZURE_OPENAI_CHAT_COMPLETIONS_URL=<AZURE_OPENAI_CHAT_COMPLETIONS_URL>
AZURE_OPENAI_RESPONSES_URL=<AZURE_OPENAI_RESPONSES_URL>
AZURE_OPENAI_V1_RESPONSES_URL=<AZURE_OPENAI_V1_RESPONSES_URL>
AZURE_OPENAI_API_KEY=<AZURE_OPENAI_API_KEY>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add -f run.yaml
lf test model azure-openai-chat-completion
lf test model azure-openai-responses
lf test model azure-openai-v1-responses
```
