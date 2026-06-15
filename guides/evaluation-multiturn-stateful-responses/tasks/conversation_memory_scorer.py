from __future__ import annotations


def compute_scores(sample, solver_output):
    # Extract the two assistant responses from the conversation trace, one per turn.
    response_0 = solver_output.trace.assistant_messages[0].content
    response_1 = solver_output.trace.assistant_messages[1].content

    return {
        "name_mentioned_response_0": sample["name"] in response_0,
        "name_mentioned_response_1": sample["name"] in response_1,
        "correct_answer_response_0": sample["answer_0"] in response_0,
        "correct_answer_response_1": sample["answer_1"] in response_1,
    }
