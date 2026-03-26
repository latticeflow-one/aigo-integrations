# Evaluation Zip Package

## Overview

This guide shows an example of initializing, configuring, and running an evaluation
using a ZIP package from URL.

## Evaluation ZIP Structure

### Minimal Structure

In order to be used with the `lf init` CLI command, an evaluation ZIP package must contain
a `run.yaml` file at its root. The `run.yaml` file is the entry point for the evaluation
and contains or references all necessary entities (e.g. datasets, models, tasks, etc.)
that are required to run the evaluation.

**Important**: The `run.yaml` may not reference any files outside the root of the ZIP
package (using `$ref`, `!include` or dataset `file_path`). All file references must be
relative to the root of the ZIP package.

### Optional Files for Ease of Use

It is recommended to include the following files in the ZIP package for ease of use:

- `README.md`: A markdown file that describes the evaluation.
- `RUN.md`: A markdown file that describes how to configure the evaluation.

### Recommended Structure

It is recommended to use the following structure for the evaluation ZIP package:

```
evaluation.zip/
├── run.yaml
├── evaluation.yaml
├── README.md
├── RUN.md
├── models/
│   ├── model.yaml
├── datasets/
│   ├── dataset.yaml
├── tasks/
│   ├── task.yaml
```

The `run.yaml` can then use `$ref` to reference the datasets, models, and tasks defined
in the ZIP package.

## Usage

This guide uses an OpenAI model as an example. It requires the OpenAI integration to
be configured as an environment variable `OPENAI_API_KEY` in the
terminal. To use a different model, please adjust the model configuration.

```bash
lf app add -f app.yaml
lf switch evaluation-zip-package-app
lf add model -f model.yaml
lf init --url https://github.com/latticeflow-one/aigo-integrations/raw/refs/heads/master/guides/evaluation-zip-package/evaluation.zip
MODEL_KEY=openai-gpt-4-1-nano lf run -f evaluation/run.yaml
```
