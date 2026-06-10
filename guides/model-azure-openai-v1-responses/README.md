# Azure AI Foundry OpenAI v1 Responses

## Overview

This guide shows an Azure AI Foundry integration using the OpenAI v1 Responses
API.

It targets `/openai/v1/responses` and uses `latticeflow$openai_responses`.

Use this pattern when your endpoint follows the OpenAI v1 surface.

## Usage

Create a `.env` file with:

```bash
AZURE_OPENAI_V1_RESPONSES_URL=<https://<resource>.openai.azure.com/openai/v1/responses>
AZURE_OPENAI_API_KEY=<AZURE_OPENAI_API_KEY>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add -f run.yaml
lf test model azure-openai-v1-responses
```
