"""LatticeFlow custom inference for a Dify agent-chat app.

Uses Dify's `/v1/chat-messages` streaming endpoint and returns an Open
Responses-style trace (assistant message plus any agent tool calls).

Pipeline:

    ChatCompletionInput  ->  ModelInput  ->  RawModelOutput  ->  OpenResponsesModelOutput
       (from AI GO!)          convert_        query_model        convert_model_output
                               user_input
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
from pydantic import BaseModel
from pydantic import Field

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
    """Request payload the Dify `/v1/chat-messages` endpoint accepts."""

    query: str
    user: str
    conversation_id: str = ""
    inputs: dict = Field(default_factory=dict)
    response_mode: str = "streaming"


class RawModelOutput(BaseModel):
    """The parsed SSE events, plus the user id we sent."""

    events: list
    dify_user: str


# ── Open Responses converter ──────────────────────────────────────────────


class OpenResponsesConverter:
    """Collapses Dify's SSE event stream into an ``OpenResponsesModelOutput``."""

    def build(
        self, events: list[dict[str, Any]], dify_user: str = "", **kwargs: Any
    ) -> OpenResponsesModelOutput:
        """Merge agent thoughts by id into tool call/output pairs, join answer chunks."""
        thoughts: dict[str, dict[str, Any]] = {}
        thought_order: list[str] = []
        answer_chunks: list[str] = []
        conversation_id = ""
        usage = {"num_prompt_tokens": 0, "num_completion_tokens": 0}

        for event in events:
            event_type = event.get("event")
            if event_type == "agent_thought":
                tid = event["id"]
                if tid not in thoughts:
                    thoughts[tid] = {}
                    thought_order.append(tid)
                thoughts[tid].update(
                    {
                        "tool": event.get("tool", "") or thoughts[tid].get("tool", ""),
                        "tool_input": event.get("tool_input", "")
                        or thoughts[tid].get("tool_input", ""),
                        "observation": event.get("observation", "")
                        or thoughts[tid].get("observation", ""),
                    }
                )
            elif event_type in ("agent_message", "message", "message_replace"):
                answer_chunks.append(event.get("answer", ""))
            elif event_type == "message_end":
                conversation_id = event.get("conversation_id", "") or conversation_id
                metadata_usage = (event.get("metadata") or {}).get("usage") or {}
                usage = {
                    "num_prompt_tokens": metadata_usage.get("prompt_tokens", 0),
                    "num_completion_tokens": metadata_usage.get("completion_tokens", 0),
                }

        items: list[TraceItem] = []
        for tid in thought_order:
            t = thoughts[tid]
            if not t.get("tool"):
                continue
            call_id = str(uuid.uuid4())
            items.append(
                self.build_function_call(t["tool"], t.get("tool_input", ""), call_id)
            )
            items.append(
                self.build_function_call_output(t.get("observation", ""), call_id)
            )

        items.append(
            self.build_assistant_message(
                "".join(answer_chunks), conversation_id, dify_user
            )
        )

        return OpenResponsesModelOutput(
            items=items,
            usage=self.build_usage(
                usage["num_prompt_tokens"], usage["num_completion_tokens"]
            ),
        )

    def build_function_call(
        self, tool: str, tool_input: str, call_id: str
    ) -> FunctionCall:
        """Build a ``FunctionCall`` (a tool call the agent made)."""
        return FunctionCall(
            id=str(uuid.uuid4()),
            call_id=call_id,
            name=tool,
            arguments=self._extract_tool_arguments(tool, tool_input),
            status=FunctionCallStatus.completed,
        )

    def build_function_call_output(
        self, observation: str, call_id: str
    ) -> FunctionCallOutput:
        """Build a ``FunctionCallOutput`` (a tool result)."""
        return FunctionCallOutput(
            id=str(uuid.uuid4()),
            call_id=call_id,
            output=observation,
            status=FunctionCallOutputStatusEnum.completed,
        )

    def build_assistant_message(
        self, text: str, conversation_id: str, dify_user: str
    ) -> Message:
        """Build the assistant ``Message``, carrying conversation_id/dify_user to round-trip."""
        return Message(
            id=str(uuid.uuid4()),
            status=MessageStatus.completed,
            role=MessageRole.assistant,
            content=[OutputTextContent(text=text, annotations=[])],
            conversation_id=conversation_id,
            dify_user=dify_user,
        )

    def build_usage(
        self, num_prompt_tokens: int = 0, num_completion_tokens: int = 0
    ) -> ModelUsage:
        """Build token usage from Dify's reported counts."""
        return ModelUsage(
            num_prompt_tokens=num_prompt_tokens,
            num_completion_tokens=num_completion_tokens,
        )

    @staticmethod
    def _extract_tool_arguments(tool_name: str, tool_input: str) -> str:
        """Dify wraps args as {tool_name: {...}}. Unwrap when present, else pass through."""
        if not tool_input:
            return "{}"
        try:
            parsed = json.loads(tool_input)
        except json.JSONDecodeError:
            return tool_input
        if (
            isinstance(parsed, dict)
            and tool_name in parsed
            and isinstance(parsed[tool_name], dict)
        ):
            return json.dumps(parsed[tool_name])
        return json.dumps(parsed) if isinstance(parsed, dict | list) else tool_input


# ── Implementation ────────────────────────────────────────────────────────


def convert_user_input(data: ChatCompletionInput) -> ModelInput:
    """Build the Dify request: latest user query + the user/conversation to reuse.

    Dify scopes conversation state to the `user`, so we mint a stable
    `latticeflow-<hex>` id on turn 1 and reuse the one echoed back afterwards.
    """
    messages = data.messages
    last_user = next(m for m in reversed(messages) if m.role == "user")

    conversation_id = ""
    user = ""
    for msg in reversed(messages):
        if msg.role == "assistant":
            conversation_id = getattr(msg, "conversation_id", "") or ""
            user = getattr(msg, "dify_user", "") or ""
            break
    if not user:
        user = f"latticeflow-{uuid.uuid4().hex[:12]}"

    return ModelInput(
        query=_message_text(last_user.content),
        user=user,
        conversation_id=conversation_id,
    )


def query_model(model_input: ModelInput, environment: dict[str, Any]) -> RawModelOutput:
    """POST to Dify chat-messages, consume the SSE stream, return parsed events."""
    url = environment["DIFY_URL"].rstrip("/") + "/v1/chat-messages"
    api_key = environment["DIFY_API_KEY"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    events: list[dict[str, Any]] = []
    with httpx.Client(timeout=120) as client:
        with client.stream(
            "POST", url, headers=headers, json=model_input.model_dump()
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                if not payload:
                    continue
                events.append(json.loads(payload))

    return RawModelOutput(events=events, dify_user=model_input.user)


def convert_model_output(raw: RawModelOutput) -> OpenResponsesModelOutput:
    """Convert the raw Dify SSE events into the Open Responses format AI GO! expects."""
    return OpenResponsesConverter().build(raw.events, raw.dify_user)


# ── Helpers ───────────────────────────────────────────────────────────────


def _message_text(content: Any) -> str:
    """Extract plain text from a chat-completion message ``content`` field."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [getattr(item, "text", "") for item in content]
        return "".join(p for p in parts if p)
    return str(content)


# ── Entry point ───────────────────────────────────────────────────────────


def run_inference(body: str, environment: dict[str, Any]) -> str:
    model_input = convert_user_input(
        ChatCompletionInput.model_validate(json.loads(body))
    )
    raw = query_model(model_input, environment)
    model_output = convert_model_output(raw)
    return model_output.model_dump_json()
