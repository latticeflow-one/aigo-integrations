# Policy Quality Gate

## Overview

This guide shows how to use policies to enforce quality thresholds on evaluation metrics.
Policies define rules that can flag when metric values drop below your quality
standards across evaluations.

The example policy checks that:

- The `faithfulness` metric is always computed (exists rule).
- The `faithfulness` metric exceeds 70% (threshold rule).

## Usage

Requires OpenAI integration (UI or `OPENAI_API_KEY` env var).

```bash
lf add app -f app.yaml
lf switch policy-quality-gate
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
lf set policies -f run.yaml
lf overview policies
```
