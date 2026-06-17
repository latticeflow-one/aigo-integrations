from latticeflow.core.dtypes import ChatCompletionModelOutput
from latticeflow.core.dtypes import ChatCompletionModelOutputChoice
from latticeflow.core.dtypes import ChatCompletionOutputMessage
from latticeflow.core.dtypes import Message
from latticeflow.core.dtypes import MessageRole
from latticeflow.core.dtypes import MessageStatus
from latticeflow.core.dtypes import ModelResponse
from latticeflow.core.dtypes import OutputTextContent
from latticeflow.core.dtypes import RawSample
from latticeflow.core.dtypes import SolverOutput
from latticeflow.core.dtypes import SolverTrace
from latticeflow.core.dtypes import Trace


def postprocess(
    sample: RawSample, solver_output: SolverOutput
) -> list[tuple[RawSample, SolverOutput]]:
    # Flatten the list of question / answer pairs into individual chat interactions.
    postprocessed_outputs = []

    # Split the full model answer into individual answers.
    model_response = solver_output.output.choices[0].message.content
    answers = [answer.strip() for answer in model_response.split("---")]
    if len(answers) != len(sample["questions"]):
        raise ValueError(
            f"Expected {len(sample['questions'])} answers, but got {len(answers)}. "
            f"Answer:\n{model_response}"
        )

    # Construct the new individual samples and traces.
    for question, target, answer in zip(
        sample["questions"], sample["targets"], answers
    ):
        trace = SolverTrace(trace=Trace.from_items([]), raw_outputs=[])
        trace.append_user_message(question)
        trace.add_model_response(
            ModelResponse(
                raw_output=ChatCompletionModelOutput(
                    choices=[
                        ChatCompletionModelOutputChoice(
                            message=ChatCompletionOutputMessage(
                                role="assistant", content=answer
                            )
                        )
                    ]
                ),
                items=[
                    Message(
                        id="",
                        status=MessageStatus.completed,
                        role=MessageRole.assistant,
                        content=[OutputTextContent(text=answer, annotations=[])],
                    )
                ],
            )
        )
        # Keep the full direct_ios from the original solver output.
        trace.direct_ios = solver_output.direct_ios
        postprocessed_outputs.append(({"question": question, "target": target}, trace))

    return postprocessed_outputs
