from __future__ import annotations

from latticeflow.core.dtypes import SampleScore


def compute_metrics(scores: list[SampleScore]) -> dict[str, int | float]:
    valid_scores = [s for s in scores if s.values["is_valid"]]
    return {
        "accuracy": sum(s.values["is_correct"] for s in valid_scores) / len(scores),
        "validity": len(valid_scores) / len(scores),
    }
