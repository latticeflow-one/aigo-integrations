# Azure OpenAI Models

## Overview

This guide shows Azure OpenAI integration patterns for both the Chat Completions
and Responses APIs using the Bearer token authentication.

## Usage

Configure the endpoint and the API key by creating a `.env` file.

```dotenv
AZURE_OPENAI_CHAT_COMPLETIONS_URL="https://<resource>.openai.azure.com/openai/v1/chat/completions"  # TODO: Replace '<resource>'
AZURE_OPENAI_RESPONSES_URL="https://<resource>.openai.azure.com/openai/v1/responses"  # TODO: Replace '<resource>'
AZURE_OPENAI_API_KEY=<AZURE_OPENAI_API_KEY>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add -f run.yaml
lf test model azure-openai-chat-completion
lf test model azure-openai-responses
```
