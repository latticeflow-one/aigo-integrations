# Dataset Generator with Claim Extraction Synthesizer

## Overview

This guide shows a dataset generator that extracts structured claims from
question–answer pairs using the built-in `claim_extraction` synthesizer.

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
