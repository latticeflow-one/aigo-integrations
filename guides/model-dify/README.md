# Dify Model

## Overview

This guide shows an example integration of a model hosted by Dify. The model can be 
hosted on a managed or self-hosted instance.

It uses the chat messages
[endpoint](https://docs.dify.ai/api-reference/chatflow/send-chat-message#send-chat-message).
A custom model adapter is defined to transform Dify messages into AI GO! messages.

## Usage

This guide uses a model hosted by Dify. Configure the endpoint and the API key by
creating a `.env` file.

```bash
DIFY_URL=<DIFY_URL>
DIFY_API_KEY=<DIFY_API_KEY>
```

```bash
lf app add -f app.yaml
lf switch playground-app
lf add -f run.yaml
lf test model model-dify
```
