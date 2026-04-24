# RAGFlow Model

## Overview

This guide shows an example integration of a model hosted by RAGFlow. The model can be 
hosted on a managed or self-hosted instance.

It uses the OpenAI-compatible API
[endpoint](https://docs.dify.ai/api-reference/chatflow/send-chat-message#send-chat-message).
A custom model adapter is defined to transform RAGFlow messages into AI GO! messages.

## Usage

This guide uses a model hosted by RAGFlow. Configure the endpoint and the API key by
creating a `.env` file.

```bash
RAGFLOW_URL=<RAGFLOW_URL>
RAGFLOW_API_KEY=<RAGFLOW_API_KEY>
RAGFLOW_MODEL=<RAGFLOW_MODEL>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add -f run.yaml
lf test model model-ragflow
```
