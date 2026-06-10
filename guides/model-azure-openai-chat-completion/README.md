# Azure OpenAI Chat Completions (Deployment-Scoped)

## Overview

This guide shows an Azure OpenAI integration that uses the legacy deployment-scoped
Chat Completions endpoint.

It targets `/openai/deployments/{deployment-id}/chat/completions?api-version=...`
and uses `latticeflow$openai_chat_completion`.

Azure OpenAI commonly authenticates with the `api-key` header, so this example
passes credentials via `custom_headers`.

## Usage

Create a `.env` file with:

```bash
AZURE_OPENAI_CHAT_COMPLETIONS_URL=<https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2024-10-21>
AZURE_OPENAI_API_KEY=<AZURE_OPENAI_API_KEY>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add -f run.yaml
lf test model azure-openai-chat-completion
```
