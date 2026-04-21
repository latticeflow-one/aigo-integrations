from pathlib import Path

import yaml

from latticeflow.go.dtypes import SDKRunConfig, SDKTaskResultLog
from latticeflow.go.sdk import Client

LOG_PATH = Path("task_result_log.json")

run_config = SDKRunConfig.model_validate(yaml.safe_load(Path("run.yaml").read_text()))

# --- Download ---

# Create and run the evaluation on the source app, waiting until it finishes.
client = Client(ai_app_key="my-app")
evaluation = client.create_evaluation(run_config.evaluation)
client.start_evaluation(evaluation.id, wait=True, poll_interval=5)

# Download the task result log and save it to disk.
task_result_log: SDKTaskResultLog = client.download_task_result_log(
    evaluation.task_results[0].id,
    download_path=LOG_PATH,
)

# --- Upload ---

# Switch to the destination app.
client.switch("another-app")

# Create the same evaluation on the destination app.
evaluation = client.create_evaluation(run_config.evaluation)

# Upload the saved log to the new task result.
client.upload_task_result_log(evaluation.task_results[0].id, LOG_PATH)

# Start the evaluation which leverages the uploaded task result log.
client.start_evaluation(evaluation.id, wait=True, poll_interval=5)
