# OpenAI GPT-4.1 Nano (Custom Task)

## Overview

This guide shows an example integration of OpenAI GPT-4.1 Nano integrated as a
custom task model. Note, that this is not a demo example, GPT-4.1 is a chat completion
model and is recommended to be integrated as a chat-completion task model.

The model uses the default chat completion API
[endpoint](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI API key by
creating a `.env` file.

```bash
OPENAI_API_KEY=<OPENAI_API_KEY>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add model -f models/openai_gpt_4-1-nano.yaml
```

To test the model, provide a sample input in a JSON file and run:

```bash
lf test model openai-gpt-4-1-nano-custom --model-input models/input.json
```
