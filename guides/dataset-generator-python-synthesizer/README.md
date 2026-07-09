# Dataset Generator with Python Synthesizer

## Overview

This guide shows an example of a dataset generator that uses a Python script as the
synthesizer. The dataset generator is then used to generate a sample dataset of simple
math questions.

It showcases how to generate math questions without any seed dataset, how to use
standard Python libraries and how to introduce randomness.

## Usage

```bash
lf add app -f app.yaml
lf switch dataset-generator-python-synthesizer
lf add -f run.yaml
```

If you want to iterate on the dataset generation, try:

```bash
lf test dataset -f run.yaml --key dataset-python-synthesizer --num-samples 4
```
