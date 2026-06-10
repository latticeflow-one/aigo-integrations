from pathlib import Path

import yaml

from latticeflow.core.dtypes import TaskResultLog
from latticeflow.go.dtypes import SDKRunConfig
from latticeflow.go.sdk import Client


LOG_PATH = Path("task_result_log.json")

run_config = SDKRunConfig.model_validate(yaml.safe_load(Path("run.yaml").read_text()))

# Create and run the evaluation on the source app, waiting until it finishes.
client = Client(ai_app_key="my-app")
print(f"[{client.ai_app_key}] Creating evaluation...")
evaluation = client.create_evaluation(run_config.evaluation)
print(f"[{client.ai_app_key}] Starting evaluation {evaluation.id}...")
client.start_evaluation(evaluation.id, wait=True, poll_interval=5)
print(f"[{client.ai_app_key}] Evaluation complete.")

# Download the task result log and save it to disk.
print(f"[{client.ai_app_key}] Downloading task result log to {LOG_PATH}...")
task_result_log: TaskResultLog = client.download_task_result_log(
    evaluation.task_results[0].id, download_path=LOG_PATH
)
print(f"[{client.ai_app_key}] Task result log saved to {LOG_PATH}.")
