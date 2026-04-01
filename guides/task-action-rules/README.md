# Action Rules

## Overview

This guide demonstrates how to use **action rules** to exclude specific samples from
metric calculations based on scorer outputs and sample metadata.

The task answers multilingual questions and measures answer quality using two scorers:

1. **`language_labeller`** (`purpose: "qa"`) — a utility labeler that detects whether the
   model responded in English or another language. Its output is used by the action rules
   but does not produce any metrics itself.
2. **`answer_quality`** — a model-as-a-judge scorer that rates each answer 0–100. Its
   mean score (`Mean Answer Quality`) is the primary metric, but only computed over
   samples that pass all action rules.

Three action rules demonstrate the three filter types available, each excluding samples
from the `Mean Answer Quality` metric:

- **Exclude non-English responses** — using a `FilterComparison` to exclude samples
  where the language labeler produced `OTHER` (i.e. the model didn't respond in English)
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
