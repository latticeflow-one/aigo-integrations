from __future__ import annotations

from pathlib import Path

import yaml

from latticeflow.go.dtypes import SDKRunConfig
from latticeflow.go.sdk import Client


LOG_PATH = Path("task_result_log.json")

run_config = SDKRunConfig.model_validate(yaml.safe_load(Path("run.yaml").read_text()))

# Create the same evaluation run on the destination app.
client = Client(ai_app_key="destination-app")
print(f"[{client.ai_app_key}] Creating evaluation run...")
evaluation_run = client.create_evaluation_run(
    evaluation_key=run_config.evaluation.key,
    config=run_config.config,
    run_config=run_config.run_config,
)

# Upload the saved log to the new task result.
print(f"[{client.ai_app_key}] Uploading task result log from {LOG_PATH}...")
client.upload_task_result_log(
    task_result_id=evaluation_run.task_results[0].id, log=LOG_PATH
)
print(f"[{client.ai_app_key}] Task result log uploaded.")

# Start the evaluation run which leverages the uploaded task result log.
print(f"[{client.ai_app_key}] Starting evaluation run {evaluation_run.id}...")
client.start_evaluation_run(evaluation_run.id, wait=True, poll_interval=5)
print(f"[{client.ai_app_key}] Evaluation complete.")
