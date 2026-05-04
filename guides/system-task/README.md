# System Task: Enforces HTTPS

## Overview

This guide demonstrates how to define and run a **system task** — a task that
runs a custom Python snippet to evaluate a system-level property rather than
interacting with a model or dataset.

The task `enforces-https` checks whether a URL enforces HTTPS by sending an HTTP
request (using `httpx`) and verifying that it is ultimately redirected to an
HTTPS URL. It accepts a single config parameter:

- **`url`** (`string`) — the URL to check (e.g. `"https://example.com"`).

The task produces one metric:

- **`enforces_https`** — `1` if the server redirects HTTP to HTTPS, `0` otherwise,
  along with a human-readable reason string showing the initial and final URLs.

## Usage

```bash
lf add app -f app.yaml
lf switch system-task-app
lf run -f run.yaml
```

To check a different URL, edit the `task_config.url` value in `run.yaml` before
running:

```yaml
task_config:
  url: "https://your-url-here.com"
```

