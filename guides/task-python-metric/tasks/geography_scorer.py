from __future__ import annotations

from typing import Any

from latticeflow.core.dtypes import RawSample
from latticeflow.core.dtypes import SolverOutput


def compute_scores(sample: RawSample, solver_output: SolverOutput) -> dict[str, Any]:
    model_completion = solver_output.trace.get_last_assistant_text() or ""
    is_valid = model_completion != ""
    return {
        "country": sample["country"],
        "capital": sample["capital"],
        "model_completion": model_completion,
        "is_correct": model_completion.lower().strip() == sample["capital"].lower(),
        "is_valid": is_valid,
    }
