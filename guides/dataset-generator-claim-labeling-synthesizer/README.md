# Dataset Generator with Claim Labeling Synthesizer

## Overview

This guide shows a dataset generator that labels extracted claims (for example,
supported, unsupported, or irrelevant) using the built-in `claim_labeling`
synthesizer.

## Usage

This guide uses an OpenAI model as an example. Configure the OpenAI integration
in the UI or set `OPENAI_API_KEY` in your terminal.

```bash
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```

To iterate on the generator:

```bash
lf test dataset -f run.yaml --key claim-labeling --num-samples 1
```
