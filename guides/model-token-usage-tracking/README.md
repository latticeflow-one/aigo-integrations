# Model Token Usage Tracking

## Overview

This guide shows how to report token usage from a model adapter so it is tracked and shown
in the model's usage breakdown on the LatticeFlow AI platform. A model's raw response usually
reports usage in a provider-specific shape (e.g. OpenAI's `usage.prompt_tokens`); the output
adapter must map it to LatticeFlow AI's `usage.num_prompt_tokens`/`num_completion_tokens`
schema, as shown in `model_adapters/openai_chat_completion_output.jinja`. The same schema
applies to trace-based outputs (agents, custom AI systems), where usage is set via
`ModelUsage` on `OpenResponsesModelOutput` instead of a Jinja adapter -- see
`tutorials/agents/dify/run_inference.py`.

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI API key by
creating a `.env` file.

```dotenv
OPENAI_API_KEY=<OPENAI_API_KEY>
```

```bash
lf add app -f app.yaml
lf switch model-token-usage-tracking
lf add -f run.yaml
lf test model openai-gpt-4-1-nano
```
