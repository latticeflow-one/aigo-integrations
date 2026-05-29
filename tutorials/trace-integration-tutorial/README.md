# tau2bench Trace Integration

## Overview

This tutorial shows how to convert raw [tau2bench](https://github.com/sierra-research/tau2-bench)
simulation traces into a [LatticeFlow AI GO!](https://latticeflow.ai) dataset.

`convert_tau2bench.py` reads a single tau2bench JSON file and produces two
artifacts in the current directory:

- `<name>.jsonl` — one row per simulation, where each `trace` field is a
  LatticeFlow `Trace` reconstructed from the tau2bench messages (user/assistant
  turns, tool calls, and tool results).
- `<name>.yaml` — a matching dataset spec pointing at the generated `.jsonl`.

## Download the traces

The trace files are not checked into this repository. Download and unpack them
into a `tau2bench_traces/` folder:

```bash
wget https://cdn.latticeflow.cloud/aigo-integrations/tau2bench_traces.zip
unzip tau2bench_traces.zip
```

This produces `tau2bench_traces/` containing one JSON file per model run, e.g.:

```
tau2bench_traces/
├── claude-opus-4-5_high_telecom_gpt-5.2_4trials.json
├── claude-sonnet-4-5_enabled_telecom_gpt-5.2_4trials.json
├── geminiflash-telecom.json
├── geminipro-telecom.json
├── glm-5_enabled_telecom_gpt-5.2_4trials.json
├── gpt-5.2_high_telecom_gpt-5.2_4trials.json
├── gpt-5.2_none_telecom_gpt-5.2_4trials.json
└── qwen3.5-397b-a17b_enabled_telecom_gpt-5.2_4trials.json
```

## Usage

Convert a single trace file:

```bash
python convert_tau2bench.py --input-file tau2bench_traces/gpt-5.2_high_telecom_gpt-5.2_4trials.json
```

This writes `gpt-5.2_high_telecom_gpt-5.2_4trials.jsonl` and
`gpt-5.2_high_telecom_gpt-5.2_4trials.yaml` to the current directory.

### Requirements

The script imports from `latticeflow.core.dtypes`, so run it in an environment
where the `latticeflow` package is installed.
