# System Task: Enforces HTTPS

## Overview

This guide demonstrates how to define and run a **system task** - a task that
runs a custom Python snippet to evaluate a system-level property rather than
interacting with a model or dataset.

## Usage

```bash
lf add app -f app.yaml
lf switch playground-app
lf run -f run.yaml
```

To check a different URL, edit the `task_config.url` value in `run.yaml` before
running:

```yaml
task_config:
  url: "https://your-url-here.com"
```

