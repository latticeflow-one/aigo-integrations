# Inspect AI Traces Dataset

## Overview

This guide shows how to create a dataset by ingesting traces from
[Inspect AI](https://inspect.ai-safety-institute.org.uk/) `.eval` log files. The
`inspect_ai` dataset source type reads log files from the local filesystem. No API key
is needed.

This source type requires the `traces` extra to be installed:

```bash
uv pip install 'latticeflow-go-sdk[traces]'
```

## Usage

```bash
lf add dataset -f datasets/inspect_ai_traces.yaml
```
