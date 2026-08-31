# Dify Model

## Overview

This guide shows an example integration of a model hosted by Dify. The model can be
hosted on a managed or self-hosted instance.

It uses the chat messages
[endpoint](https://docs.dify.ai/en/api-reference/chat-messages/send-chat-message).
A custom model adapter is defined to transform Dify messages into AI GO! messages.

## Usage

This guide uses a model hosted by Dify. Configure the endpoint and the API key setting environment variables
`DIFY_URL` and `DIFY_API_KEY`, respectively.

```bash
lf secret add --name DIFY_API_KEY --value $DIFY_API_KEY
lf add -f run.yaml
lf test model model-dify
```
