# Conversation Memory Evaluation

## Overview

Evaluation of a chat model's ability to remember information from previous messages in
the conversation.

The main purpose of this evaluation is to validate the model integration, especially
that the conversation history is preserved across multiple turns.

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI API key by
creating a `.env` file.

```dotenv
OPENAI_API_KEY=<OPENAI_API_KEY>
```

```bash
lf add app -f app.yaml
lf switch evaluation-multiturn-stateful-responses
lf run -f run.yaml
```
