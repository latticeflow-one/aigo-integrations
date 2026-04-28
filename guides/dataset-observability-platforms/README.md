# Datasets from Observability Platforms

## Overview

This guide shows how to create datasets by ingesting traces from observability platforms.
Four platforms are supported, each represented by a dedicated dataset source type:

- **`langsmith_traces.yaml`** — Imports traces from a
  [LangSmith](https://docs.smith.langchain.com/) project or dataset. Requires a
  LangSmith API key and endpoint URL.

- **`phoenix_traces.yaml`** — Imports traces from an
  [Arize Phoenix](https://docs.arize.com/phoenix) project. Requires a Phoenix API key
  and base URL.

- **`claude_code_traces.yaml`** — Imports traces from local
  [Claude Code](https://docs.anthropic.com/en/docs/claude-code) session files.
  No API key is needed; sessions are read from the local filesystem
  (`~/.claude/projects/` by default).

- **`inspect_ai_traces.yaml`** — Imports traces from
  [Inspect AI](https://inspect.ai-safety-institute.org.uk/) `.eval` log files stored
  locally. No API key is needed; provide a path to a log file or directory.

All four source types require the `traces` extra to be installed:

```bash
pip install 'latticeflow-go-sdk[traces]'
```

## Usage

Configure the required environment variables for the platforms you plan to use by
creating a `.env` file.

```bash
# LangSmith
LANGSMITH_API_KEY=<LANGSMITH_API_KEY>
LANGSMITH_ENDPOINT_URL=<LANGSMITH_ENDPOINT_URL>
LANGSMITH_PROJECT=<LANGSMITH_PROJECT>

# Arize Phoenix
PHOENIX_API_KEY=<PHOENIX_API_KEY>
PHOENIX_BASE_URL=<PHOENIX_BASE_URL>
PHOENIX_PROJECT=<PHOENIX_PROJECT>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add dataset -f datasets/langsmith_traces.yaml
lf add dataset -f datasets/phoenix_traces.yaml
lf add dataset -f datasets/claude_code_traces.yaml
lf add dataset -f datasets/inspect_ai_traces.yaml
```
