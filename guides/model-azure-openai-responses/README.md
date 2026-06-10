# Azure OpenAI Responses (Legacy OpenAI Surface)

## Overview

This guide shows an Azure OpenAI integration using the Responses API on the
legacy `/openai` surface.

It targets `/openai/responses` and uses `latticeflow$openai_responses`.

This pattern is useful when your Azure OpenAI endpoint supports Responses but you
are not using the newer `/openai/v1` surface yet.

## Usage

Create a `.env` file with:

```bash
AZURE_OPENAI_RESPONSES_URL=<https://<resource>.openai.azure.com/openai/responses>
AZURE_OPENAI_API_KEY=<AZURE_OPENAI_API_KEY>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add -f run.yaml
lf test model azure-openai-responses
```
