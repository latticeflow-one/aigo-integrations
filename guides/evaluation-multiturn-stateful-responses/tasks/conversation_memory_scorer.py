def compute_scores(sample, solver_output):
    # Extract the assistant responses from the conversation defined by the solver.
    response_0 = solver_output.messages[2]
    assert response_0["role"] == "assistant"
    response_1 = solver_output.messages[4]
    assert response_1["role"] == "assistant"

    return {
        "name_mentioned_response_0": sample["name"] in response_0["content"],
        "name_mentioned_response_1": sample["name"] in response_1["content"],
        "correct_answer_response_0": sample["answer_0"] in response_0["content"],
        "correct_answer_response_1": sample["answer_1"] in response_1["content"],
    }
