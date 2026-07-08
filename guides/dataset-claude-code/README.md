# Claude Code Traces Dataset

## Overview

This guide shows how to create a dataset by ingesting traces from local
[Claude Code](https://docs.anthropic.com/en/docs/claude-code) session files. The
`claude_code` dataset source type reads sessions from the local filesystem
(`~/.claude/projects/` by default). No API key is needed.

This source type requires the `traces` extra to be installed:

```bash
uv pip install 'latticeflow-go-sdk[traces]'
```

## Usage

```bash
lf add app -f app.yaml
lf switch dataset-claude-code-traces
lf add dataset -f datasets/claude_code_traces.yaml
```
