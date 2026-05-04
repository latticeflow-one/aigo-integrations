# OpenCode Session Traces Dataset

## Overview

This guide shows how to export OpenCode coding agent sessions and convert them into
an AI GO! Trace dataset. The pipeline exports raw session data from the local OpenCode
database, converts each session into the Open Responses trace format (with sub-agent
spans, tool calls, and model usage metadata), and registers the resulting JSONL file
as a dataset.

## Usage

**1. Export sessions from the local OpenCode database:**

Requires `opencode` CLI installed.

```bash
./export_sessions.sh [output_dir]
```

This writes each session as a JSON file into `./session_data/` (or the specified
output directory). Sessions that have already been exported are skipped.

**2. Convert exported sessions to Trace JSONL:**

```bash
python convert_sessions.py [--num-samples N] [--session-dir DIR] [--output FILE]
```

This reads the exported JSON files, selects root sessions (excluding sub-agent
sessions), converts them to `Trace` objects, and writes the output to
`opencode_traces.jsonl`. By default it samples 10 sessions; use `--num-samples 0`
to convert all.

**3. Register the dataset:**

```bash
lf add dataset -f opencode_traces.yaml
```
