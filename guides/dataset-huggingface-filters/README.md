# HuggingFace Dataset Filters

## Overview

This guide shows how to filter HuggingFace datasets using the three available filter
operators. Three dataset examples are included:

- **`harmbench_illegal.yaml`** — Filters the [HarmBench evaluation dataset](https://huggingface.co/datasets/allenai/tulu-3-harmbench-eval)
  to only include rows where `SemanticCategory` equals `illegal`. Demonstrates `op: "equals"` (`FilterComparison`).

- **`harmbench_not_in.yaml`** — Filters the same HarmBench dataset to exclude
  `copyright` and `chemical_biological` categories. Demonstrates `op: "not_in"` (`FilterMembership`).

- **`boolq_is_true.yaml`** — Filters the [BoolQ dataset](https://huggingface.co/datasets/google/boolq)
  to only include samples where the `answer` column is `true`. Demonstrates `op: "is_true"` (`FilterUnary`).

## Usage

```bash
lf app add -f app.yaml
lf switch playground-app
lf add dataset -f datasets/harmbench_illegal.yaml
lf add dataset -f datasets/harmbench_not_in.yaml
lf add dataset -f datasets/boolq_is_true.yaml
```
