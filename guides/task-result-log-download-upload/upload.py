from pathlib import Path

import yaml

from latticeflow.go.dtypes import SDKRunConfig
from latticeflow.go.sdk import Client


LOG_PATH = Path("task_result_log.json")

run_config = SDKRunConfig.model_validate(yaml.safe_load(Path("run.yaml").read_text()))

# Create the same evaluation on the destination app.
client = Client(ai_app_key="destination-app")
print(f"[{client.ai_app_key}] Creating evaluation...")
evaluation = client.create_evaluation(run_config.evaluation)

# Upload the saved log to the new task result.
print(f"[{client.ai_app_key}] Uploading task result log from {LOG_PATH}...")
client.upload_task_result_log(evaluation.task_results[0].id, LOG_PATH)
print(f"[{client.ai_app_key}] Task result log uploaded.")

# Start the evaluation which leverages the uploaded task result log.
print(f"[{client.ai_app_key}] Starting evaluation {evaluation.id}...")
client.start_evaluation(evaluation.id, wait=True, poll_interval=5)
print(f"[{client.ai_app_key}] Evaluation complete.")
