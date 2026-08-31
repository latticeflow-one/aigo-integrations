from pathlib import Path

import yaml

from latticeflow.core.dtypes import TaskResultLog
from latticeflow.go.dtypes import SDKRunConfig
from latticeflow.go.sdk import Client


LOG_PATH = Path("task_result_log.json")

run_config = SDKRunConfig.model_validate(yaml.safe_load(Path("run.yaml").read_text()))

# Create and start the evaluation run on the source app, waiting until it finishes.
client = Client(ai_app_key="source-app")
print(f"[{client.ai_app_key}] Creating evaluation run...")
evaluation_run = client.create_evaluation_run(
    evaluation_key=run_config.evaluation.key,
    config=run_config.config,
    run_config=run_config.run_config,
)
print(f"[{client.ai_app_key}] Starting evaluation run {evaluation_run.id}...")
client.start_evaluation_run(
    evaluation_run_id=evaluation_run.id, wait=True, poll_interval=5
)
print(f"[{client.ai_app_key}] Evaluation run complete.")

# Download the task result log and save it to disk.
print(f"[{client.ai_app_key}] Downloading task result log to {LOG_PATH}...")
task_result_log: TaskResultLog = client.download_task_result_log(
    task_result_id=evaluation_run.task_results[0].id, download_path=LOG_PATH
)
print(f"[{client.ai_app_key}] Task result log saved to {LOG_PATH}.")
