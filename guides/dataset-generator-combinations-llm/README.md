# Dataset Generator: Combinations + LLM Synthesizer

## Overview

This guide shows how to generate a dataset from all pairwise combinations of two source
datasets using an LLM synthesizer.

The generator combines a `cities` dataset and a `languages` dataset, then uses an LLM
to produce a question-answer pair for each city-language combination.

## Usage

Requires OpenAI integration (UI or `OPENAI_API_KEY` env var).

```sh
lf app add -f app.yaml
lf switch playground-app
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```
