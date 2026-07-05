# Dataset Generator with Link Claim Quotes Synthesizer

## Overview

This guide shows a dataset generator that links extracted claims to verbatim
quotes in the candidate answer using the built-in `link_claim_quotes` synthesizer.

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI integration
in the UI or set `OPENAI_API_KEY` in your terminal.

```bash
lf add app -f app.yaml
lf switch dataset-generator-link-claim-quotes
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

To iterate on the generator:

```bash
lf test dataset -f run.yaml --key link-claim-quotes --num-samples 1
```
