from __future__ import annotations

from typing import Any


def compute_scores(sample: dict[str, Any], solver_output: Any) -> dict[str, Any]:
    model_completion = solver_output.output["choices"][0]["message"]["content"]
    is_valid = model_completion != ""
    return {
        "country": sample["country"],
        "capital": sample["capital"],
        "model_completion": model_completion,
        "is_correct": model_completion.lower().strip() == sample["capital"].lower(),
        "is_valid": is_valid,
    }
