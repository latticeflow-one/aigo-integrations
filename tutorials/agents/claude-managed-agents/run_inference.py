"""LatticeFlow custom inference for a Claude Managed Agents deployment.

Creates (or reuses) a Managed Agents session, streams a `user.message`, and
converts the resulting session-event stream into an Open Responses trace
(assistant message + MCP tool calls + tool outputs).

The Anthropic SDK auto-attaches `anthropic-beta: managed-agents-2026-04-01`
for any call through `client.beta.sessions.*`.

Pipeline:

    ChatCompletionInput  ->  ModelInput  ->  RawModelOutput  ->  OpenResponsesModelOutput
       (from AI GO!)          convert_        query_model        convert_model_output
                              user_input
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import anthropic
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


# Stop reasons that mean the turn is over.
_TERMINAL_STOP_REASONS = {"end_turn", "retries_exhausted"}

# Tool-call event types fetched from spawned subthreads (coordinator topologies).
_SUBTHREAD_TOOL_EVENT_TYPES = frozenset({"agent.mcp_tool_use", "agent.mcp_tool_result"})


# ── Model-side types ──────────────────────────────────────────────────────


class ModelInput(BaseModel):
    """Request payload the Managed Agents session accepts."""

    session_id: str = ""  # empty on the first turn, reused afterwards
    user_message: str


class RawModelOutput(BaseModel):
    """The collected session events, plus the session id we used."""

    session_id: str
    events: list


# ── Open Responses converter ──────────────────────────────────────────────


class OpenResponsesConverter:
    """Converts a Managed Agents event stream into an ``OpenResponsesModelOutput``."""

    def build(
        self, events: list[dict[str, Any]], session_id: str = "", **kwargs: Any
    ) -> OpenResponsesModelOutput:
        """Convert the session events into ordered Open Responses items."""
        items: list[TraceItem] = []
        num_prompt_tokens = 0
        num_completion_tokens = 0
        answer_chunks: list[str] = []

        for event in events:
            event_type = event.get("type")
            if event_type == "agent.mcp_tool_use":
                items.append(self.build_function_call(event))
            elif event_type == "agent.mcp_tool_result":
                items.append(self.build_function_call_output(event))
            elif event_type == "agent.message":
                chunk = self._join_text_blocks(event.get("content"))
                if chunk:
                    answer_chunks.append(chunk)
            elif event_type == "span.model_request_end":
                usage = event.get("model_usage") or {}
                num_prompt_tokens += usage.get("input_tokens", 0) or 0
                num_completion_tokens += usage.get("output_tokens", 0) or 0

        items.append(self.build_assistant_message("".join(answer_chunks), session_id))

        return OpenResponsesModelOutput(
            items=items,
            usage=self.build_usage(num_prompt_tokens, num_completion_tokens),
        )

    def build_function_call(self, event: dict[str, Any]) -> FunctionCall:
        """Build a ``FunctionCall`` from an ``agent.mcp_tool_use`` event."""
        return FunctionCall(
            id=str(uuid.uuid4()),
            call_id=event["id"],
            name=event["name"],
            arguments=json.dumps(event.get("input") or {}),
            status=FunctionCallStatus.completed,
        )

    def build_function_call_output(self, event: dict[str, Any]) -> FunctionCallOutput:
        """Build a ``FunctionCallOutput`` from an ``agent.mcp_tool_result`` event."""
        return FunctionCallOutput(
            id=str(uuid.uuid4()),
            call_id=event["mcp_tool_use_id"],
            output=self._tool_result_output(event),
            status=FunctionCallOutputStatusEnum.completed,
        )

    def build_assistant_message(self, text: str, session_id: str) -> Message:
        """Build the assistant ``Message``, carrying ``session_id`` to round-trip."""
        return Message(
            id=str(uuid.uuid4()),
            status=MessageStatus.completed,
            role=MessageRole.assistant,
            content=[OutputTextContent(text=text, annotations=[])],
            session_id=session_id,
        )

    def build_usage(
        self, num_prompt_tokens: int = 0, num_completion_tokens: int = 0
    ) -> ModelUsage:
        """Build token usage from the summed per-request counts."""
        return ModelUsage(
            num_prompt_tokens=num_prompt_tokens,
            num_completion_tokens=num_completion_tokens,
        )

    @staticmethod
    def _join_text_blocks(blocks: list[dict[str, Any]] | None) -> str:
        if not blocks:
            return ""
        parts: list[str] = []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "".join(parts)

    @classmethod
    def _tool_result_output(cls, event: dict[str, Any]) -> str:
        """Flatten tool-result content list into a single string for the LF trace."""
        text = cls._join_text_blocks(event.get("content"))
        if text:
            return text
        if event.get("is_error"):
            return json.dumps({"error": True, "content": event.get("content")})
        return json.dumps(event.get("content") or [])


# ── Implementation ────────────────────────────────────────────────────────


def convert_user_input(data: ChatCompletionInput) -> ModelInput:
    """Pull the latest user turn + reuse a session_id echoed by a prior assistant."""
    messages = data.messages
    last_user = next(m for m in reversed(messages) if m.role == "user")

    session_id = ""
    for msg in reversed(messages):
        if msg.role == "assistant":
            session_id = getattr(msg, "session_id", "") or ""
            break

    return ModelInput(
        session_id=session_id, user_message=_message_text(last_user.content)
    )


def query_model(model_input: ModelInput, environment: dict[str, Any]) -> RawModelOutput:
    """Create/reuse a session, send `user.message`, collect events until idle.

    Also pulls tool-call events from any subthreads the agent spawned so the
    trace reflects coordinator topologies, not just the primary stream.
    """
    client = anthropic.Anthropic(api_key=environment["ANTHROPIC_API_KEY"])

    session_id = model_input.session_id
    if not session_id:
        session_id = _create_session(client, environment)

    events: list[dict[str, Any]] = []
    with client.beta.sessions.events.stream(session_id) as stream:
        client.beta.sessions.events.send(
            session_id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": model_input.user_message}],
                }
            ],
        )
        for event in stream:
            events.append(_serialise_event(event))
            if event.type == "session.status_idle":
                stop_reason = getattr(event, "stop_reason", None)
                stop_type = getattr(stop_reason, "type", None)
                if stop_type in _TERMINAL_STOP_REASONS:
                    break

    for thread_id in _collect_subthread_ids(events):
        events.extend(_fetch_subthread_tool_events(client, session_id, thread_id))

    return RawModelOutput(session_id=session_id, events=events)


def convert_model_output(raw: RawModelOutput) -> OpenResponsesModelOutput:
    """Convert the raw session events into the Open Responses format AI GO! expects."""
    return OpenResponsesConverter().build(raw.events, raw.session_id)


# ── Helpers ───────────────────────────────────────────────────────────────


def _message_text(content: Any) -> str:
    """Extract plain text from a chat-completion message ``content`` field."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [getattr(item, "text", "") for item in content]
        return "".join(p for p in parts if p)
    return str(content)


def _create_session(client: anthropic.Anthropic, environment: dict[str, Any]) -> str:
    session = client.beta.sessions.create(
        agent=environment["CLAUDE_AGENT_ID"],
        environment_id=environment["CLAUDE_ENVIRONMENT_ID"],
        vault_ids=[environment["CLAUDE_VAULT_ID"]],
    )
    return session.id


def _serialise_event(event: Any) -> dict[str, Any]:
    """Convert an SDK event model to a plain dict for the raw payload."""
    return event.model_dump(mode="json")


def _collect_subthread_ids(events: list[dict[str, Any]]) -> list[str]:
    """Return all subthread ids referenced from the primary thread, in order."""
    seen: list[str] = []
    for event in events:
        thread_id = (
            event.get("session_thread_id")
            or event.get("to_session_thread_id")
            or event.get("from_session_thread_id")
        )
        if thread_id and thread_id not in seen:
            seen.append(thread_id)
    return seen


def _fetch_subthread_tool_events(
    client: anthropic.Anthropic, session_id: str, thread_id: str
) -> list[dict[str, Any]]:
    """List a subthread's tool-call events (use + result) for trace enrichment."""
    return [
        _serialise_event(event)
        for event in client.beta.sessions.threads.events.list(
            thread_id, session_id=session_id
        )
        if getattr(event, "type", None) in _SUBTHREAD_TOOL_EVENT_TYPES
    ]


# ── Entry point ───────────────────────────────────────────────────────────


def run_inference(body: str, environment: dict[str, Any]) -> str:
    model_input = convert_user_input(
        ChatCompletionInput.model_validate(json.loads(body))
    )
    raw = query_model(model_input, environment)
    model_output = convert_model_output(raw)
    return model_output.model_dump_json()
