def compute_scores(sample: dict, model_input: dict, model_output: dict) -> dict:
    return {
        "job_id": sample["job_id"],
        "variant": sample["variant"],
        "model_output": model_output,
    }
