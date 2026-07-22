# Model with Sample Dependent Inference

## Overview

This guide shows an example integration of a model with sample dependent inference logic.

Concretely, it shows that run_inference snippet can receive the dataset sample and use it's content when interacting with the AI system.

## Usage

```bash
lf add app -f app.yaml
lf switch model-sample-dependent-inference
lf run -f run.yaml
```

or test an invididual sample using:

```bash
lf test task -f run.yaml --spec-key example-task-with-sample-dependent-inference --num-samples 1
```