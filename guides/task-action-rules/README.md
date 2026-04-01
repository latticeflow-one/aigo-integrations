# Action Rules

## Overview

This guide demonstrates how to use **action rules** to exclude specific samples from
metric calculations based on scorer outputs and sample metadata.

The task answers multilingual questions and labels the language of each model response.
Three action rules demonstrate the three filter types available:

- **Exclude non-English responses** — using a `FilterComparison` to exclude samples
  where the language labeler produced `OTHER`
- **Exclude specific sample IDs** — using a `FilterMembership` to exclude a fixed
  list of sample IDs (for example, samples reserved for manual inspection)
- **Exclude holdout samples** — using a `FilterUnary` to exclude samples flagged in
  the dataset as held out

## Usage

```bash
lf app add -f app.yaml
lf switch action-rules-app
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```
