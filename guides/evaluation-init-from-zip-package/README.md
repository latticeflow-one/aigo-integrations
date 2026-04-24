# Initialize and Run Evaluation from ZIP Package

## Overview

This guide shows an example of initializing, configuring, and running an evaluation
from a ZIP package from URL, using the `lf init` CLI command.

Concretely, this guide:

1. Adds a new app and custom model.
2. Fetches the ZIP package `evaluation.zip` using `lf init --url`.
3. Configures the evaluation by setting the `$MODEL_KEY` environment variable.
4. Runs the evaluation using `lf run`.

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
lf add app -f app.yaml
lf switch playground-app
lf add model -f model.yaml
lf init --url https://github.com/latticeflow-one/aigo-integrations/raw/refs/heads/master/guides/evaluation-init-from-zip-package/evaluation.zip
MODEL_KEY=openai-gpt-4-1-nano lf run -f evaluation/run.yaml
```
