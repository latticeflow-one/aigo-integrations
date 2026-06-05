"""LatticeFlow custom inference for an Azure AI Foundry agent.

Calls the Foundry agent through its OpenAI-compatible Responses API
(via `azure-ai-projects`' `project.get_openai_client()`), using an
`agent_reference` `extra_body` to target the deployed agent.

Multi-turn state is kept in Foundry's own `conversations` API — the adapter
creates one on the first turn and echoes the `conversation_id` back in the
assistant message so subsequent turns reuse it.

Auth: when the service-principal values (`AZURE_TENANT_ID` / `AZURE_CLIENT_ID` /
`AZURE_CLIENT_SECRET`) are present in ``environment`` — as injected by
`model.yaml` in the LatticeFlow runtime — a `ClientSecretCredential` is built
from them directly. Otherwise it falls back to `DefaultAzureCredential` (e.g.
the local `az login` token).

Pipeline:

    ChatCompletionInput  ->  ModelInput  ->  RawModelOutput  ->  OpenResponsesModelOutput
       (from AI GO!)          convert_        query_model        convert_model_output
                              user_input
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import ClientSecretCredential
from azure.identity import DefaultAzureCredential
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
    """Request payload the Foundry Responses call needs."""

    conversation_id: str = ""  # empty on the first turn, reused afterwards
    user_message: str


class RawModelOutput(BaseModel):
    """The Foundry response output items, plus the conversation id and usage."""

    conversation_id: str
    output: list
    usage: dict = Field(default_factory=dict)


# ── Open Responses converter ──────────────────────────────────────────────


class OpenResponsesConverter:
    """Converts Foundry Responses output items into an ``OpenResponsesModelOutput``."""

    def build(
        self,
        output_items: list[dict[str, Any]],
        conversation_id: str = "",
        usage: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> OpenResponsesModelOutput:
        """Convert the response output items into ordered Open Responses items.

        Each ``mcp_call`` becomes a ``function_call`` + ``function_call_output``
        pair; assistant ``message`` text is joined into a single reply.
        ``mcp_list_tools`` and other informational items are skipped.
        """
        items: list[TraceItem] = []
        answer_chunks: list[str] = []

        for item in output_items:
            item_type = item.get("type")
            if item_type == "mcp_call":
                call_id = item["id"]
                items.append(self.build_function_call(item, call_id))
                items.append(self.build_function_call_output(item, call_id))
            elif item_type == "message" and item.get("role") == "assistant":
                chunk = self._join_output_text(item.get("content"))
                if chunk:
                    answer_chunks.append(chunk)

        items.append(
            self.build_assistant_message("".join(answer_chunks), conversation_id)
        )

        return OpenResponsesModelOutput(
            items=items, usage=self.build_usage(usage or {})
        )

    def build_function_call(self, item: dict[str, Any], call_id: str) -> FunctionCall:
        """Build a ``FunctionCall`` from an ``mcp_call`` output item."""
        return FunctionCall(
            id=str(uuid.uuid4()),
            call_id=call_id,
            name=item.get("name") or "",
            arguments=item.get("arguments") or "{}",
            status=FunctionCallStatus.completed,
        )

    def build_function_call_output(
        self, item: dict[str, Any], call_id: str
    ) -> FunctionCallOutput:
        """Build a ``FunctionCallOutput`` from an ``mcp_call`` output item."""
        return FunctionCallOutput(
            id=str(uuid.uuid4()),
            call_id=call_id,
            output=self._mcp_call_output(item),
            status=FunctionCallOutputStatusEnum.completed,
        )

    def build_assistant_message(self, text: str, conversation_id: str) -> Message:
        """Build the assistant ``Message``, carrying ``conversation_id`` to round-trip."""
        return Message(
            id=str(uuid.uuid4()),
            status=MessageStatus.completed,
            role=MessageRole.assistant,
            content=[OutputTextContent(text=text, annotations=[])],
            conversation_id=conversation_id,
        )

    def build_usage(self, usage: dict[str, Any]) -> ModelUsage:
        """Build token usage from Foundry's reported counts."""
        return ModelUsage(
            num_prompt_tokens=usage.get("input_tokens", 0) or 0,
            num_completion_tokens=usage.get("output_tokens", 0) or 0,
        )

    @staticmethod
    def _join_output_text(content_blocks: list[dict[str, Any]] | None) -> str:
        if not content_blocks:
            return ""
        parts: list[str] = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "output_text":
                parts.append(block.get("text") or "")
        return "".join(parts)

    @staticmethod
    def _mcp_call_output(item: dict[str, Any]) -> str:
        """Flatten an mcp_call's stringified output (or error) into a trace value."""
        output = item.get("output")
        if isinstance(output, str) and output:
            return output
        error = item.get("error")
        if error:
            return json.dumps({"error": error})
        if output is None:
            return ""
        return json.dumps(output)


# ── Implementation ────────────────────────────────────────────────────────


def convert_user_input(data: ChatCompletionInput) -> ModelInput:
    """Pull the latest user turn + reuse a conversation_id from a prior assistant."""
    messages = data.messages
    last_user = next(m for m in reversed(messages) if m.role == "user")

    conversation_id = ""
    for msg in reversed(messages):
        if msg.role == "assistant":
            conversation_id = getattr(msg, "conversation_id", "") or ""
            break

    return ModelInput(
        conversation_id=conversation_id, user_message=_message_text(last_user.content)
    )


def _build_credential(environment: dict[str, Any]) -> Any:
    """Service-principal creds from ``environment`` if present, else az-login default.

    The LatticeFlow sandbox passes the SP values in ``environment`` (not as OS
    env vars), so ``DefaultAzureCredential``'s ``EnvironmentCredential`` can't
    see them — build a ``ClientSecretCredential`` explicitly instead.
    """
    tenant_id = environment.get("AZURE_TENANT_ID")
    client_id = environment.get("AZURE_CLIENT_ID")
    client_secret = environment.get("AZURE_CLIENT_SECRET")
    if tenant_id and client_id and client_secret:
        return ClientSecretCredential(tenant_id, client_id, client_secret)
    return DefaultAzureCredential()


def query_model(model_input: ModelInput, environment: dict[str, Any]) -> RawModelOutput:
    """Open/reuse a Foundry conversation, call the agent, return raw output items."""
    credential = _build_credential(environment)
    project_client = AIProjectClient(
        endpoint=environment["AZURE_AI_PROJECT_ENDPOINT"], credential=credential
    )

    with project_client, project_client.get_openai_client() as openai_client:
        conversation_id = model_input.conversation_id
        if not conversation_id:
            conversation = openai_client.conversations.create()
            conversation_id = conversation.id

        response = openai_client.responses.create(
            conversation=conversation_id,
            input=model_input.user_message,
            extra_body={
                "agent_reference": {
                    "name": environment["AZURE_FOUNDRY_AGENT_NAME"],
                    "type": "agent_reference",
                }
            },
        )

    output = [item.model_dump(mode="json") for item in response.output]
    usage = response.usage.model_dump(mode="json") if response.usage else {}
    return RawModelOutput(conversation_id=conversation_id, output=output, usage=usage)


def convert_model_output(raw: RawModelOutput) -> OpenResponsesModelOutput:
    """Convert the raw Foundry output into the Open Responses format AI GO! expects."""
    return OpenResponsesConverter().build(raw.output, raw.conversation_id, raw.usage)


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
