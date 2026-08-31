# OpenCode Session Traces Dataset

## Overview

This guide shows how to turn your local [OpenCode](https://opencode.ai) coding
agent sessions into a trace dataset in AI GO!, so you can browse, evaluate, and
benchmark past agent runs alongside other datasets.

Requires the `opencode` CLI installed and on `PATH`.

## Usage

The commands below export raw sessions from the local OpenCode database into
`datasets/session_data/` as one JSON file per session, convert the root
sessions (excluding sub-agent sessions) into the
[Open Responses](https://www.openresponses.org/) trace format and write them
to `datasets/opencode_traces.jsonl` (one trace per line, with sub-agent spans,
tool calls, and model usage metadata), and register that JSONL as a dataset.

By default, 10 sessions are exported and converted. Use `--num-samples 0` to
process all sessions.

```bash
cd datasets
./export_sessions.sh --num-samples 10 ./session_data
python convert_sessions.py --session-dir ./session_data --output ./opencode_traces.jsonl
cd ..
lf add dataset -f datasets/opencode_traces.yaml
```
