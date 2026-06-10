# Azure OpenAI Models

## Overview

This guide shows three Azure OpenAI integration patterns:

1. Deployment-scoped Chat Completions (`/openai/deployments/{deployment-id}/chat/completions?api-version=...`)
2. Responses on the `/openai` surface (`/openai/responses`)
3. OpenAI v1 Responses (`/openai/v1/responses`)

The examples include both `api-key` and `authorization` header patterns.

## Usage

Create a `.env` file with the variables required by the model variant you want to test.

### 1) Chat Completions (`azure-openai-chat-completion`)

```bash
AZURE_OPENAI_CHAT_COMPLETIONS_URL=https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2024-10-21
AZURE_OPENAI_API_KEY=<your_api_key>
# Optional alternative to api-key header:
# AZURE_OPENAI_AUTHORIZATION=Bearer <token>
```

### 2) `/openai/responses` (`azure-openai-responses`)

```bash
AZURE_OPENAI_RESPONSES_URL=https://<resource>.openai.azure.com/openai/responses
AZURE_OPENAI_API_KEY=<your_api_key>
# Optional alternative to api-key header:
# AZURE_OPENAI_AUTHORIZATION=Bearer <token>
```

### 3) `/openai/v1/responses` (`azure-openai-v1-responses`)

```bash
AZURE_OPENAI_V1_RESPONSES_URL=https://<resource>.openai.azure.com/openai/v1/responses
AZURE_OPENAI_API_KEY=<your_api_key>
# Optional alternative to api-key header:
# AZURE_OPENAI_AUTHORIZATION=Bearer <token>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add -f run.yaml
# Run the test(s) for the model(s) you configured in .env
lf test model azure-openai-chat-completion
lf test model azure-openai-responses
lf test model azure-openai-v1-responses
```
