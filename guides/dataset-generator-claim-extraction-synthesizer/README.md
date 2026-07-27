# Dataset Generator with Claim Extraction Synthesizer

## Overview

This guide shows a dataset generator that extracts structured claims from
question–answer pairs using the built-in `claim_extraction` synthesizer.

## Resulting dataset

The single inline source sample

```json
{
  "question": "What is the capital of France?",
  "expected_answer": "The capital of France is Paris. Paris is well known for its Eiffel Tower."
}
```

produces one output sample, which keeps the source columns and adds a `claims`
column holding one `(subject, predicate, object)` triplet per extracted fact:

```json
{
  "question": "What is the capital of France?",
  "expected_answer": "The capital of France is Paris. Paris is well known for its Eiffel Tower.",
  "claims": [
    {"claim": {"subject": "Paris", "predicate": "is the capital of", "object": "France"}},
    {"claim": {"subject": "Paris", "predicate": "is well known for its", "object": "Eiffel Tower"}}
  ]
}
```

The claims are extracted by a model, so the exact triplets vary between runs.

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI integration
in the UI or set `OPENAI_API_KEY` in your terminal.

```bash
lf add app -f app.yaml
lf switch dataset-generator-claim-extraction
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

To iterate on the generator:

```bash
lf test dataset -f run.yaml --key claim-extraction --num-samples 1
```
