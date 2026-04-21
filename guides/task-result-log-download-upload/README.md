# Downloading and Uploading Task Result Logs

## Overview

This guide shows how to download and upload task result logs across AI apps and
deployments. This flow is helpful when you need to populate an AI app with results
previously computed for another AI app without the need to rerun inference or
recompute the scores.

You can create and run an evaluation, and also download and upload task result logs
using both the SDK client and the CLI. We show both approaches. We first address
prerequisites of this example.

## Prerequisites

For this example, you will need an OpenAI integration and one AI app with entities
which can be used for the subsequent evaluation.

1. Add OpenAI integration.

```bash
lf integration add --provider openai --api-key $OPENAI_API_KEY
```

2. Create the source AI app and switch to it.

```bash
lf add app -f apps/my_app.yaml
lf switch my-app
```

3. Populate it with entities.

```bash
lf add -f run.yaml
```

## Download (CLI)

1. Run the evaluation in the source app (wait until it finishes).

```bash
lf run -f run.yaml --wait
```

2. Export the results together with linked task result logs. This allows you
   to upload the results to a second AI app.

```bash
lf export eval --id <eval ID> --output results --link-logs
```

Note that you will now obtain a new run config at `./results/foobarization-evaluation.yaml`
with the task result logs linked, i.e., the evaluation section of the YAML will look like this:

```yaml
evaluation:
  key: foobarization-evaluation
  ...
  task_specifications:
    - key: foobarization-spec
      ...
      task_result_log_path: task_results/foobarization-spec/task_result_log.json
```

## Upload (CLI)

1. Create the destination AI app and switch to it.

```bash
lf add app -f apps/another_app.yaml
lf switch another-app
```

2. Populate it with entities.

```bash
lf add -f run.yaml
```

3. Upload the results. This will populate the evaluation so that you can see
   the results for the second AI app as well, without the need to rerun the evaluation.

```bash
lf run -f results/foobarization-evaluation.yaml --wait
```

## Usage (SDK)

See [download_upload.py](download_upload.py) for a complete script that demonstrates
the same flow using the Python SDK client.
