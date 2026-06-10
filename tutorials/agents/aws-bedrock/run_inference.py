"""LatticeFlow custom inference for an AWS Bedrock AgentCore Harness.

Calls `bedrock-agentcore.invoke_harness` and converts the Converse-style event
stream (messageStart / contentBlockStart / contentBlockDelta / contentBlockStop
/ messageStop / metadata) into an Open Responses trace.

Multi-turn state lives in AgentCore's per-session microVM keyed by
`runtimeSessionId` — the adapter mints a UUID on the first turn (≥ 33 chars as
Harness requires) and echoes it back on the assistant message so subsequent
turns reuse the same session.

Auth is explicit: the AWS access key id + secret are read from the
``environment`` dict passed in (which the LF runtime populates from `model.yaml`
secrets). boto3's default credential chain is intentionally *not* used — the
adapter must not depend on `~/.aws/credentials`, `aws sso login`, or any AWS CLI
tooling being present in the runtime image.

Pipeline:

    ChatCompletionInput  ->  ModelInput  ->  RawModelOutput  ->  OpenResponsesModelOutput
       (from AI GO!)          convert_        query_model        convert_model_output
                              user_input
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import boto3
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
    """Request payload the Harness invocation needs."""

    session_id: str = ""  # empty on the first turn, reused afterwards
    user_message: str


class RawModelOutput(BaseModel):
    """The collected Converse event stream, plus the session id we used."""

    session_id: str
    events: list


# ── Open Responses converter ──────────────────────────────────────────────


class OpenResponsesConverter:
    """Converts the Harness Converse event stream into an ``OpenResponsesModelOutput``."""

    def build(
        self, events: list[dict[str, Any]], session_id: str = "", **kwargs: Any
    ) -> OpenResponsesModelOutput:
        """Accumulate the event stream into finalised blocks, then convert them.

        Each tool-use block becomes a ``function_call``, each tool-result block a
        ``function_call_output``, and assistant text is joined into one reply.
        """
        blocks, usage = self._accumulate_stream(events)

        items: list[TraceItem] = []
        answer_chunks: list[str] = []
        for block in blocks:
            kind = block["kind"]
            if kind == "tool_use":
                items.append(self.build_function_call(block))
            elif kind == "tool_result":
                items.append(self.build_function_call_output(block))
            elif kind == "text":
                answer_chunks.append(block["text"])

        items.append(self.build_assistant_message("".join(answer_chunks), session_id))

        return OpenResponsesModelOutput(items=items, usage=self.build_usage(usage))

    def build_function_call(self, block: dict[str, Any]) -> FunctionCall:
        """Build a ``FunctionCall`` from a finalised tool-use block."""
        return FunctionCall(
            id=str(uuid.uuid4()),
            call_id=block["tool_use_id"],
            name=block["name"],
            arguments=block.get("input_json") or "{}",
            status=FunctionCallStatus.completed,
        )

    def build_function_call_output(self, block: dict[str, Any]) -> FunctionCallOutput:
        """Build a ``FunctionCallOutput`` from a finalised tool-result block."""
        return FunctionCallOutput(
            id=str(uuid.uuid4()),
            call_id=block["tool_use_id"],
            output=block.get("output") or "",
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

    def build_usage(self, usage: dict[str, int]) -> ModelUsage:
        """Build token usage from the accumulated counts."""
        return ModelUsage(
            num_prompt_tokens=usage.get("num_prompt_tokens", 0),
            num_completion_tokens=usage.get("num_completion_tokens", 0),
        )

    @staticmethod
    def _stringify_tool_result(blocks: list[Any] | None) -> str:
        """Flatten a toolResult `[{text|json}]` content list into a single string."""
        if not blocks:
            return ""
        parts: list[str] = []
        for entry in blocks:
            if not isinstance(entry, dict):
                continue
            text = entry.get("text")
            if isinstance(text, str) and text:
                parts.append(text)
                continue
            payload = entry.get("json")
            if payload is not None:
                parts.append(json.dumps(payload))
        return "".join(parts)

    @classmethod
    def _accumulate_stream(
        cls, events: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Walk the event stream once, emitting finalised content blocks in order.

        Each emitted block is one of:
          - {"kind": "text", "role": "assistant", "text": "..."}
          - {"kind": "tool_use", "tool_use_id": "...", "name": "...", "input_json": "..."}
          - {"kind": "tool_result", "tool_use_id": "...", "output": "...", "status": "..."}

        A second return value carries token usage from the trailing `metadata`
        event. Converse streams interleave multiple messages per turn (assistant
        with toolUse → user with toolResult → assistant final), each with content
        blocks indexed by `contentBlockIndex`, so we keep a small state machine
        keyed by `(message_index, content_block_index)`.
        """
        blocks: list[dict[str, Any]] = []
        usage: dict[str, int] = {"num_prompt_tokens": 0, "num_completion_tokens": 0}

        message_index = -1
        current_role = "assistant"
        active: dict[tuple[int, int], dict[str, Any]] = {}

        def _finalise(msg_idx: int, block_idx: int) -> None:
            state = active.pop((msg_idx, block_idx), None)
            if state is None:
                return
            kind = state.get("kind")
            if kind == "text":
                text = state.get("text") or ""
                if text and state.get("role") == "assistant":
                    blocks.append({"kind": "text", "role": "assistant", "text": text})
            elif kind == "tool_use":
                blocks.append(
                    {
                        "kind": "tool_use",
                        "tool_use_id": state.get("tool_use_id") or "",
                        "name": state.get("name") or "",
                        "input_json": state.get("input_json") or "",
                    }
                )
            elif kind == "tool_result":
                blocks.append(
                    {
                        "kind": "tool_result",
                        "tool_use_id": state.get("tool_use_id") or "",
                        "output": cls._stringify_tool_result(
                            state.get("output_chunks") or []
                        ),
                        "status": state.get("status") or "success",
                    }
                )

        for event in events:
            if "messageStart" in event:
                message_index += 1
                current_role = event["messageStart"].get("role") or "assistant"
                continue

            if "contentBlockStart" in event:
                payload = event["contentBlockStart"]
                block_idx = int(payload.get("contentBlockIndex") or 0)
                start = payload.get("start") or {}
                tool_use = start.get("toolUse")
                tool_result = start.get("toolResult")
                if tool_use:
                    active[(message_index, block_idx)] = {
                        "kind": "tool_use",
                        "tool_use_id": tool_use.get("toolUseId") or "",
                        "name": tool_use.get("name") or "",
                        "input_json": "",
                    }
                elif tool_result:
                    active[(message_index, block_idx)] = {
                        "kind": "tool_result",
                        "tool_use_id": tool_result.get("toolUseId") or "",
                        "status": tool_result.get("status") or "success",
                        "output_chunks": [],
                    }
                else:
                    # Empty `start` means a plain text block — the first delta tells us.
                    active[(message_index, block_idx)] = {
                        "kind": None,
                        "role": current_role,
                    }
                continue

            if "contentBlockDelta" in event:
                payload = event["contentBlockDelta"]
                block_idx = int(payload.get("contentBlockIndex") or 0)
                delta = payload.get("delta") or {}
                state = active.get((message_index, block_idx))
                if state is None:
                    state = {"kind": None, "role": current_role}
                    active[(message_index, block_idx)] = state

                if "text" in delta and delta["text"]:
                    if state.get("kind") is None:
                        state["kind"] = "text"
                        state["text"] = ""
                    state["text"] = (state.get("text") or "") + delta["text"]
                elif "toolUse" in delta:
                    tu = delta["toolUse"] or {}
                    state["kind"] = "tool_use"
                    state["input_json"] = (state.get("input_json") or "") + (
                        tu.get("input") or ""
                    )
                elif "toolResult" in delta:
                    state["kind"] = "tool_result"
                    state.setdefault("output_chunks", []).extend(
                        delta["toolResult"] or []
                    )
                continue

            if "contentBlockStop" in event:
                payload = event["contentBlockStop"]
                block_idx = int(payload.get("contentBlockIndex") or 0)
                _finalise(message_index, block_idx)
                continue

            if "metadata" in event:
                metadata_usage = event["metadata"].get("usage") or {}
                usage["num_prompt_tokens"] += int(
                    metadata_usage.get("inputTokens") or 0
                )
                usage["num_completion_tokens"] += int(
                    metadata_usage.get("outputTokens") or 0
                )
                continue

            # messageStop / errors are not needed for trace construction.

        # Flush any blocks left open by truncated streams so we don't lose content.
        for msg_idx, block_idx in list(active.keys()):
            _finalise(msg_idx, block_idx)

        return blocks, usage


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
    """Invoke the harness, collect the event stream, return raw events + session id.

    Credentials are taken **only** from ``environment``; boto3's default chain
    (shared credentials file, SSO cache, instance metadata) is bypassed by
    passing the access key explicitly. ``AWS_SESSION_TOKEN`` is optional.
    """
    client = boto3.client(
        "bedrock-agentcore",
        region_name=environment.get("AWS_REGION") or "eu-central-1",
        aws_access_key_id=environment["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=environment["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=environment.get("AWS_SESSION_TOKEN") or None,
    )

    session_id = model_input.session_id or _new_session_id()

    response = client.invoke_harness(
        harnessArn=environment["AWS_HARNESS_ARN"],
        runtimeSessionId=session_id,
        messages=[{"role": "user", "content": [{"text": model_input.user_message}]}],
    )

    events: list[dict[str, Any]] = list(response["stream"])
    return RawModelOutput(session_id=session_id, events=events)


def convert_model_output(raw: RawModelOutput) -> OpenResponsesModelOutput:
    """Convert the raw Converse event stream into the Open Responses format."""
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


def _new_session_id() -> str:
    """Harness requires runtimeSessionId ≥ 33 chars; uuid4 string is 36."""
    return str(uuid.uuid4())


# ── Entry point ───────────────────────────────────────────────────────────


def run_inference(body: str, environment: dict[str, Any]) -> str:
    model_input = convert_user_input(
        ChatCompletionInput.model_validate(json.loads(body))
    )
    raw = query_model(model_input, environment)
    model_output = convert_model_output(raw)
    return model_output.model_dump_json()
