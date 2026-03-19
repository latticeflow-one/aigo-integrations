# HuggingFace Dataset

## Overview

This guide shows an example integration of a dataset hosted by HuggingFace.

The dataset is sourced from the [HarmBench evaluation dataset on HuggingFace](https://huggingface.co/datasets/allenai/tulu-3-harmbench-eval)
and filtered before the upload.

## Usage

```bash
lf app add -f app.yaml
lf switch playground-app
lf add dataset -f datasets/dataset.yaml
```
