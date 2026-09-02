# Downloading and Uploading Task Result Logs

## Overview

This guide shows how to download and upload task result logs to AI GO!.

- Download a task result log to inspect evidence locally, feed results into analysis pipelines, integrate with third-party tools, or transfer results to another AI app.
- Upload a task result log to reproduce results in another AI app, reuse a cached run without rerunning inference, or save time and cost.

## Download Task Result Log

Downloading a task result log exports the inference outputs and scores from a completed evaluation run to disk, along with snapshots of all entities used in the evaluation.

1. If you don't have a source AI app with a completed evaluation, set one up first, otherwise skip this section. Add an OpenAI integration, create the source AI app, and run the evaluation.

```bash
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf add app -f apps/my_app.yaml
lf switch source-app
lf run -f run.yaml --wait
```

2. Export the results together with linked task result logs to analyze, postprocess, or integrate with external tools.

```bash
lf export eval-run --id <evaluation run ID> --output results --link-logs
```

You can also use the Python SDK with [download.py](download.py).

```bash
python download.py
```

## Upload Task Result Log

Uploading a task result log injects pre-computed inference outputs and scores into a new evaluation run.

1. If you don't have a destination AI app with entities set up, create one first, otherwise skip this step. Create the destination AI app, and populate it with entities.

```bash
lf add app -f apps/another_app.yaml
lf switch destination-app
lf add -f run.yaml
```

2. Upload the results to the destination app. This will populate the evaluation so that you can see the results without rerunning inference.

```bash
lf run -f results/is-foobarized.yaml --wait
```

You can also use the Python SDK with [upload.py](upload.py).

```bash
python upload.py
```
