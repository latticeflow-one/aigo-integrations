"""LatticeFlow custom inference for a Dify agent-chat app.

Uses Dify's `/v1/chat-messages` streaming endpoint and returns an Open
Responses-style trace (assistant message plus any agent tool calls).

The integration runs as a three-stage pipeline, mirroring the AI GO!
`run_inference` template:

    ChatCompletionInput  ->  ModelInput  ->  RawModelOutput  ->  OpenResponsesModelOutput
       (from AI GO!)          convert_        query_model        convert_model_output
                              user_input
"""

# Example body (LatticeFlow -> run_inference)
# {
#   "messages": [
#     {"role": "user", "content": "Search the catalog for shoes."}
#   ]
# }
#
# Multi-turn (subsequent turns include prior assistant message with extras):
# {
#   "messages": [
#     {"role": "user", "content": "Hello!"},
#     {"role": "assistant", "content": "Hello! How can I assist you today?",
#      "conversation_id": "a12690e1-cda8-4bf2-acfc-b588d6846425",
#      "dify_user": "latticeflow-dc4f1f002667"},
#     {"role": "user", "content": "What is my conversation id?"}
#   ]
# }

# Example raw model output (agent API -> query_model)
# Dify streams SSE events; query_model returns the parsed event list plus the
# user identifier we sent (so convert_model_output can echo it back).
# {
#   "dify_user": "latticeflow-5fa47d159030",
#   "events": [
#     {"event": "agent_thought", "id": "239b...", "position": 1,
#      "tool": "search_products",
#      "tool_input": "{\"search_products\": {\"query\": \"shoes\"}}",
#      "observation": "{\"search_products\": \"... result=[] ...\"}"},
#     {"event": "agent_message", "answer": "It looks "},
#     {"event": "agent_message", "answer": "like there are no products..."},
#     {"event": "message_end",
#      "conversation_id": "cdb01cc3-3754-4f36-91b9-df643506a982",
#      "metadata": {"usage": {"prompt_tokens": 407, "completion_tokens": 51}}}
#   ]
# }

# Example LF model output (convert_model_output)
# {
#   "items": [
#     {"type": "function_call", "id": "5bf9...", "call_id": "97eb...",
#      "name": "search_products", "arguments": "{\"query\": \"shoes\"}",
#      "status": "completed"},
#     {"type": "function_call_output", "id": "9da4...", "call_id": "97eb...",
#      "output": "{\"search_products\": \"... result=[] ...\"}",
#      "status": "completed"},
#     {"type": "message", "id": "44c2...", "status": "completed",
#      "role": "assistant",
#      "content": [{"type": "output_text", "text": "It looks like ...",
#                   "annotations": []}],
#      "conversation_id": "cdb01cc3-3754-4f36-91b9-df643506a982",
#      "dify_user": "latticeflow-5fa47d159030"}
#   ],
#   "usage": {"num_prompt_tokens": 407, "num_completion_tokens": 51}
# }

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
from pydantic import BaseModel
from pydantic import Field

from latticeflow.core.dtypes import AssistantMessage
from latticeflow.core.dtypes import ChatCompletionInput
from latticeflow.core.dtypes import FunctionCall
from latticeflow.core.dtypes import FunctionCallOutput
from latticeflow.core.dtypes import FunctionCallOutputStatusEnum
from latticeflow.core.dtypes import FunctionCallStatus
from latticeflow.core.dtypes import MessageStatus
from latticeflow.core.dtypes import ModelUsage
from latticeflow.core.dtypes import OpenResponsesModelOutput
from latticeflow.core.dtypes import OutputTextContent
from latticeflow.core.dtypes import TraceItem


# ── Model-side types ──────────────────────────────────────────────────────


class ModelInput(BaseModel):
    """Request payload the Dify `/v1/chat-messages` endpoint accepts.

    Produced by ``convert_user_input`` and consumed by ``query_model``.
    """

    query: str
    user: str
    conversation_id: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    response_mode: str = "streaming"


class RawModelOutput(BaseModel):
    """Raw response returned by the Dify endpoint.

    Dify streams Server-Sent Events; ``query_model`` parses them into a flat
    ``events`` list and carries the ``dify_user`` so it can be echoed back to
    AI GO! for multi-turn continuity.
    """

    events: list[dict[str, Any]]
    dify_user: str


# ── Open Responses converter ──────────────────────────────────────────────


class OpenResponsesConverter:
    """Converts Dify's SSE event stream into an ``OpenResponsesModelOutput``.

    Dify streams partial, repeated events rather than role-tagged messages, so
    ``build`` first collapses the stream (agent thoughts merged by id, answer
    chunks joined) and then constructs the Open Responses items in one pass.
    """

    def build(
        self,
        events: list[dict[str, Any]],
        dify_user: str = "",
        **kwargs: Any,
    ) -> OpenResponsesModelOutput:
        """Collapse the Dify event stream and convert it into Open Responses items.

        Agent thoughts are merged by id (Dify emits the same thought id across
        several partial events) into ordered tool call / tool output pairs, and
        the streamed answer chunks are joined into a single assistant message.
        """
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
    ) -> AssistantMessage:
        """Build the assistant ``AssistantMessage`` from the joined answer text.

        ``conversation_id`` and ``dify_user`` are attached as extra fields so
        AI GO! round-trips them back on the next turn, keeping the conversation
        pinned to the same Dify-side thread.
        """
        return AssistantMessage(
            id=str(uuid.uuid4()),
            status=MessageStatus.completed,
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
    """Build the Dify chat-messages request from LatticeFlow input.

    Dify scopes per-conversation state (memory, agent thoughts) to the `user`
    field, so every turn for the same thread must send the *same* user
    identifier. We mint a fresh `latticeflow-<hex>` id on turn 1 and reuse the
    one the assistant echoed back on subsequent turns; this avoids pinning
    every conversation to the same Dify-side bucket.
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
