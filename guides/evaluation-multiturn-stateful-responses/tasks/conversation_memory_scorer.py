from __future__ import annotations

from typing import Any

from latticeflow.core.dtypes import RawSample
from latticeflow.core.dtypes import SolverOutput


def compute_scores(sample: RawSample, solver_output: SolverOutput) -> dict[str, Any]:
    # Extract the two assistant responses from the conversation trace, one per turn.
    response_0 = solver_output.trace.assistant_messages[0].content
    response_1 = solver_output.trace.assistant_messages[1].content

    return {
        "name_mentioned_response_0": sample["name"] in response_0,
        "name_mentioned_response_1": sample["name"] in response_1,
        "correct_answer_response_0": sample["answer_0"] in response_0,
        "correct_answer_response_1": sample["answer_1"] in response_1,
    }
