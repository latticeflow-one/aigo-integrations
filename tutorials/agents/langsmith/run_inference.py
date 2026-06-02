"""LatticeFlow custom inference for a LangGraph Platform deployment.

Calls `POST /threads/{thread_id}/runs/wait` on a LangSmith-managed LangGraph
deployment and returns the full agent trace (tool calls + final reply) in
the Open Responses shape.

A single inference runs as a three-stage pipeline:

    ChatCompletionInput  ->  ModelInput  ->  RawModelOutput  ->  OpenResponsesModelOutput
       (from AI GO!)          convert_        query_model        convert_model_output
                              user_input

`run_inference` ties the stages together: it parses the request body, converts
it to what the LangGraph endpoint accepts, calls the endpoint, and converts the
raw response back into the Open Responses format AI GO! expects.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
from pydantic import BaseModel

from latticeflow.core.dtypes import ChatCompletionInput
from latticeflow.core.dtypes import FunctionCall
from latticeflow.core.dtypes import FunctionCallOutput
from latticeflow.core.dtypes import FunctionCallOutputStatusEnum
from latticeflow.core.dtypes import FunctionCallStatus
from latticeflow.core.dtypes import Message
from latticeflow.core.dtypes import MessageRole
from latticeflow.core.dtypes import MessageStatus
from latticeflow.core.dtypes import ModelUsage
from latticeflow.core.dtypes import OpenResponsesModelOutput
from latticeflow.core.dtypes import OutputTextContent
from latticeflow.core.dtypes import TraceItem


# ── Model-side types ──────────────────────────────────────────────────────


class ModelInput(BaseModel):
    """Request payload the LangGraph endpoint accepts.

    Produced by ``convert_user_input`` and consumed by ``query_model``.
    ``thread_id`` is empty on the first turn and reused on subsequent turns.
    """

    thread_id: str
    user_message: str


class RawModelOutput(BaseModel):
    """Raw response returned by the LangGraph ``/runs/wait`` endpoint.

    ``final_state`` is the full thread state; ``thread_id`` is the thread we
    used, carried through so ``convert_model_output`` can echo it back.
    """

    thread_id: str
    final_state: dict


# ── Open Responses converter ──────────────────────────────────────────────


class OpenResponsesConverter:
    """Converts LangGraph per-turn messages into an ``OpenResponsesModelOutput``."""

    def build(self, messages: list[Any], **kwargs: Any) -> OpenResponsesModelOutput:
        """Convert raw LangGraph turn messages into an ``OpenResponsesModelOutput``."""
        items: list[TraceItem] = []
        num_prompt_tokens = 0
        num_completion_tokens = 0
        for message in messages:
            msg_type = message.get("type")
            if msg_type == "ai":
                # One `ai` message may carry several tool calls and/or text.
                for call in message.get("tool_calls") or []:
                    items.append(self.build_function_call(call, **kwargs))
                content = message.get("content") or ""
                if isinstance(content, str) and content.strip():
                    items.append(self.build_assistant_message(message, **kwargs))

                # Token usage is reported once per `ai` message.
                usage = message.get("usage_metadata") or {}
                num_prompt_tokens += usage.get("input_tokens", 0) or 0
                num_completion_tokens += usage.get("output_tokens", 0) or 0
            elif msg_type == "tool":
                items.append(self.build_function_call_output(message, **kwargs))
            else:
                raise ValueError(f"Unhandled message type: `{msg_type}`")

        return OpenResponsesModelOutput(
            items=items,
            usage=self.build_usage(num_prompt_tokens, num_completion_tokens),
        )

    def build_assistant_message(self, message: dict, **kwargs: Any) -> Message:
        return Message(
            id=str(uuid.uuid4()),
            status=MessageStatus.completed,
            role=MessageRole.assistant,
            content=[OutputTextContent(text=message["content"], annotations=[])],
            # Carried as an extra field so the next turn can reuse the thread.
            thread_id=kwargs.get("thread_id", ""),
        )

    def build_function_call(self, call: dict, **kwargs: Any) -> FunctionCall:
        return FunctionCall(
            id=str(uuid.uuid4()),
            call_id=call["id"],
            name=call["name"],
            arguments=json.dumps(call.get("args") or {}),
            status=FunctionCallStatus.completed,
        )

    def build_function_call_output(
        self, message: dict, **kwargs: Any
    ) -> FunctionCallOutput:
        return FunctionCallOutput(
            id=str(uuid.uuid4()),
            call_id=message["tool_call_id"],
            output=message.get("content") or "",
            status=FunctionCallOutputStatusEnum.completed,
        )

    def build_usage(
        self, num_prompt_tokens: int = 0, num_completion_tokens: int = 0
    ) -> ModelUsage:
        return ModelUsage(
            num_prompt_tokens=num_prompt_tokens,
            num_completion_tokens=num_completion_tokens,
        )


# ── Implementation ─────────────────────────────────────────────────────────


def convert_user_input(data: ChatCompletionInput) -> ModelInput:
    """Pull the latest user turn + reuse a thread_id echoed by a prior assistant."""
    messages = data.messages
    last_user = next(m for m in reversed(messages) if m.role == "user")

    thread_id = ""
    for msg in reversed(messages):
        if msg.role == "assistant":
            thread_id = getattr(msg, "thread_id", "") or ""
            break

    return ModelInput(thread_id=thread_id, user_message=last_user.content)


def query_model(model_input: ModelInput, environment: dict[str, Any]) -> RawModelOutput:
    """Create a thread if needed, then POST /runs/wait and return final state."""
    base_url = environment["LANGSMITH_DEPLOY_URL"].rstrip("/")
    api_key = environment["LANGSMITH_API_KEY"]
    assistant_id = environment["LANGGRAPH_ASSISTANT_ID"]

    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    with httpx.Client(timeout=120) as client:
        thread_id = model_input.thread_id
        if not thread_id:
            create = client.post(f"{base_url}/threads", headers=headers, json={})
            create.raise_for_status()
            thread_id = create.json()["thread_id"]

        run = client.post(
            f"{base_url}/threads/{thread_id}/runs/wait",
            headers=headers,
            json={
                "assistant_id": assistant_id,
                "input": {
                    "messages": [{"role": "user", "content": model_input.user_message}]
                },
            },
        )
        run.raise_for_status()
        final_state = run.json()

    return RawModelOutput(thread_id=thread_id, final_state=final_state)


def convert_model_output(raw_model_output: RawModelOutput) -> OpenResponsesModelOutput:
    """Convert the raw LangGraph response into the Open Responses format.

    `/runs/wait` returns the FULL thread state, so first keep only the messages
    produced by THIS turn (everything after the last human message), then run the
    converter over them.
    """
    thread_id = raw_model_output.thread_id
    messages = raw_model_output.final_state.get("messages", [])

    last_human = -1
    for i, msg in enumerate(messages):
        if msg.get("type") == "human":
            last_human = i
    turn_messages = messages[last_human + 1 :] if last_human >= 0 else messages

    return OpenResponsesConverter().build(turn_messages, thread_id=thread_id)


# ── Entry point ───────────────────────────────────────────────────────────


def run_inference(body: str, environment: dict[str, Any]) -> str:
    # 1. Parse and convert the request into the model's input format.
    model_input = convert_user_input(
        ChatCompletionInput.model_validate(json.loads(body))
    )

    # 2. Query the LangGraph endpoint (creating a thread on the first turn).
    response = query_model(model_input, environment)

    # 3. Convert the raw response into the format AI GO! expects.
    model_output = convert_model_output(response)

    return model_output.model_dump_json()
