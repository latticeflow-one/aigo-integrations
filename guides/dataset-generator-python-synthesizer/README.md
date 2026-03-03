# Dataset Generator with Python Synthesizer

## Overview

This guide shows an example of a dataset generator that uses a Python script as the
synthesizer. The dataset generator is then used to generate a sample dataset.

## Usage

```bash
lf app add -f app.yaml
lf switch playground-app 
lf run -f run.yaml
```

If you want to iterate on the dataset generation, try:

```bash
lf test dataset -f run.yaml --key dataset-python-synthesizer --num-samples 4
```
