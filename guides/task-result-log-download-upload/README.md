# Downloading and Uploading Task Result Logs

## Overview

This guide shows how to download and upload task result logs from one evaluation
to another. This flow is helpful when you need to populate an AI app with results
previously computed for another AI app without the need to rerun inference or
recompute the scores.

You can create and run an evaluation, and also downlaod and upload task result logs
using both the SDK client and the CLI. We show both both approaches. We first address
prerequisites of this example.

## Prerequisites

For this example, you will need an OpenAI integration and two AI apps with entities
which can be used for the subsequent evaluations.

1. Add OpenAI integration.

```bash
lf integration add --provider openai --api-key $OPENAI_API_KEY
```

2. Create the two AI apps.

```bash
lf add app -f apps/my_app.yaml
lf add app -f apps/another_app.yaml
```

3. Switch to the first one and populate it with entities.

```bash
lf switch my-app
lf add -f run.yaml
```

4. Switch to the second one and populate it with entities.

```bash
lf switch another-app
lf add -f run.yaml
```

5. Switch back to the first one.

```bash
lf switch my-app
```

## Usage (CLI)

1. Run the evaluation in the first app (wait until it finishes).

```bash
lf run -f run.yaml --wait
```

2. Export the results together with linked task result logs. This allows you
   to upload the results to the second AI app.

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

3. Switch to the second app and upload the results there. This will populate the evaluation so
   that you can see the results for the second AI app as well, without the need to rerun the evaluation.

```bash
lf switch another-app
lf run -f results/foobarization-evaluation.yaml --wait
```

## Usage (SDK)

1. Load the run config from `run.yaml` and extract the evaluation definition.

```python
from pathlib import Path
import yaml
from latticeflow.go.sdk import Client
from latticeflow.go.dtypes import SDKRunConfig, SDKTaskResultLog

LOG_PATH = Path("task_result_log.json")

run_config = SDKRunConfig.model_validate(yaml.safe_load(Path("run.yaml").read_text()))
```

2. Create and run the evaluation on the first app, waiting until it finishes.

```python
client = Client(ai_app_key="my-app")
evaluation = client.create_evaluation(run_config.evaluation)
client.start_evaluation(evaluation.id, wait=True, poll_interval=5)
```

3. Download the task result log and save it to disk.

```python
task_result_log: SDKTaskResultLog = client.download_task_result_log(
    evaluation.task_results[0].id,
    download_path=LOG_PATH,
)
```

4. Switch to the second app.

```python
client.switch("another-app")
```

5. Create the same evaluation on the second app.

```python
evaluation = client.create_evaluation(run_config.evaluation)
```

6. Upload the saved log to the new task result.

```python
client.upload_task_result_log(evaluation.task_results[0].id, LOG_PATH)
```

7. Start the evaluation which leverages the uploaded task result log

```python
client.start_evaluation(evaluation.id, wait=True, poll_interval=5)
```
