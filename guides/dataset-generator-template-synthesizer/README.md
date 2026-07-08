# Dataset Generator with Template Synthesizer

## Overview

This guide shows an example of a dataset generator that uses a Jinja template in the
synthesizer. The dataset generator is then used to generate a sample dataset.

## Usage

```bash
lf add app -f app.yaml
lf switch dataset-generator-template-synthesizer
lf run -f run.yaml
```

If you want to iterate on the dataset generation, try:

```bash
lf test dataset -f run.yaml --key qa-generated-from-template --num-samples 4
```
