# Dataset in JSONL Format

## Overview

This guide shows an example integration of a dataset in JSONL format, and how to
filter it using the three available filter operators. All examples are built on
the same `data.jsonl` file of adversarial prompt-injection samples. Each sample
carries a `language`, `technique` and `jailbreak` field alongside its `text`.

### Basic dataset

- **`dataset.yaml`** — Loads the full `data.jsonl` dataset without any filtering.

### Filtered datasets

- **`english_prompts.yaml`** — Filters the dataset to only include samples where the
  `language` field equals `English`. Demonstrates `op: "equals"` (`FilterComparison`).

- **`non_roleplay_prompts.yaml`** — Filters the dataset to exclude the `role_playing` and
  `context_manipulation` techniques. Demonstrates `op: "not_in"` (`FilterMembership`).

- **`jailbreak_prompts.yaml`** — Filters the dataset to only include samples flagged as
  jailbreak attempts. Demonstrates `op: "is_true"` (`FilterUnary`).

## Usage

```bash
lf add app -f app.yaml
lf switch playground-app
lf add dataset -f datasets/dataset.yaml
lf add dataset -f datasets/english_prompts.yaml
lf add dataset -f datasets/non_roleplay_prompts.yaml
lf add dataset -f datasets/jailbreak_prompts.yaml
```
