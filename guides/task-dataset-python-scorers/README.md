# Data Quality Tasks

## Overview

This guide shows an example of two tasks that evaluate the data quality of a dataset.
It evaluates the completeness of dataset samples using a single-sample Python scorer
and the uniqueness of dataset samples using an all-samples Python scorer.

## Usage

```bash
lf add app -f app.yaml
lf switch task-dataset-python-scorers
lf run -f run.yaml
```

If you want to iterate on the task definitions, try:

```bash
lf test task -f run.yaml -sk uniqueness-task-hello-dataset -n 10
lf test task -f run.yaml -sk completeness-task-hello-dataset -n 10
```
