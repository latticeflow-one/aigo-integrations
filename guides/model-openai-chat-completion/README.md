# OpenAI Chat Completion Model

## Overview

This guide shows an example integration of OpenAI GPT-4.1 Nano model without the use of
any built-in models or model adapters.

The model uses the default chat completion API
[endpoint](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).


Moreover, it shows how to integrate a model such that its token usage is tracked in the AI Platform.
A model's raw response usually reports token usage in a provider-specific shape (e.g. OpenAI's `usage.prompt_tokens`).

To track this, the output model adapter must map it to LatticeFlow AI's `usage.num_prompt_tokens/num_completion_tokens` schema, see [example](./model_adapters/openai_chat_completion_output.jinja).
The same schema applies to trace-based outputs (agents, custom AI systems), where usage is set via `ModelUsage` on `OpenResponsesModelOutput` instead of a Jinja adapter, see [example](../../tutorials/agents/dify/run_inference.py).

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI API key by
creating a `.env` file.

```dotenv
OPENAI_API_KEY=<OPENAI_API_KEY>
```

```bash
lf add -f run.yaml
lf test model openai-gpt-4-1-nano
```
