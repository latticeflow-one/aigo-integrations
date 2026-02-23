# Conversation Memory Evaluation

## Overview

Evaluation of a chat model's ability to remember information from previous messages in
the conversation.

The main purpose of this evaluation is to validate the model integration, especially
that the conversation history is preserved across multiple turns.

## Usage

```bash
lf app add -f app.yaml
lf switch conversation_memory
export OPENAI_API_KEY="..."
lf run -f run.yaml
```
