# Dataset Generator with Template Synthesizer

## Overview

This guide shows an example of a dataset generator that uses a Jinja template in the
synthesizer. The dataset generator is then used to generate a sample dataset.

## Usage

Note, this guide uses expects OPENAI_API_KEY defined.
To use a different model, please adjust the model configuration.

```bash
lf app add -f app.yaml
lf switch playground-app
lf integration add --provider openai --api-key $OPENAI_API_KEY 
lf run -f run.yaml

lf dataset generation-preview datasets/qa-generated-from-template.yaml --num-samples 4
```
