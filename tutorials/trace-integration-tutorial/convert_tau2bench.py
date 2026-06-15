"""Convert a tau2bench JSON trace file into a LatticeFlow AI GO dataset.

Reads a single tau2bench simulation JSON from --input-file, writes a .jsonl
dataset and a matching dataset YAML spec to the current directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

import yaml

from latticeflow.core.dtypes import AssistantMessage
from latticeflow.core.dtypes import FunctionCall
from latticeflow.core.dtypes import FunctionCallOutput
from latticeflow.core.dtypes import FunctionCallOutputStatusEnum
from latticeflow.core.dtypes import FunctionCallStatus
from latticeflow.core.dtypes import InputTextContent
from latticeflow.core.dtypes import OutputTextContent
from latticeflow.core.dtypes import SYNTHETIC_MESSAGE_STATUS
from latticeflow.core.dtypes import Trace
from latticeflow.core.dtypes import TraceItem
from latticeflow.core.dtypes import UserMessage


class Tau2BenchMessageConverter:
    """Converts tau2bench message dicts into LatticeFlow TraceItems.

    Processes messages sequentially.  Tool results are matched to preceding
    ``FunctionCall`` items via a queue of pending call-ids, because some
    providers (e.g. Gemini) omit the ``id`` field on tool-result messages.

    Usage::

        converter = Tau2BenchMessageConverter()
        trace_items = converter.convert(messages)
    """

    def __init__(self) -> None:
        self.items: list[TraceItem] = []
        self.pending_calls: dict[str, str] = {}  # original_call_id -> role

    @staticmethod
    def short_call_id(call_id: str) -> str:
        """Hash a long call_id to a 12-char hex string."""
        return hashlib.sha256(call_id.encode()).hexdigest()[:12]

    # ------------------------------------------------------------------
    # Per-type conversion methods
    # ------------------------------------------------------------------

    def convert_user_content(self, content: str) -> None:
        """Append a ``UserMessage`` for a user's text content."""
        self.items.append(
            UserMessage(
                id=str(uuid.uuid4()),
                status=SYNTHETIC_MESSAGE_STATUS,
                content=[InputTextContent(text=content)],
            )
        )

    def convert_assistant_content(self, content: str) -> None:
        """Append an ``AssistantMessage`` for an assistant's text content."""
        self.items.append(
            AssistantMessage(
                id=str(uuid.uuid4()),
                status=SYNTHETIC_MESSAGE_STATUS,
                content=[OutputTextContent(text=content, annotations=[])],
            )
        )

    def convert_tool_result(self, message: dict[str, Any]) -> None:
        """Append a ``FunctionCallOutput``, matching it to a pending call.

        Prefers an explicit ``id`` on the message; falls back to the oldest
        pending call (FIFO) when the id is absent.
        """
        content = message.get("content")
        original_call_id = message.get("id")

        if original_call_id is None:
            if not self.pending_calls:
                original_call_id = str(uuid.uuid4())
            else:
                # Pop the oldest pending call (FIFO).
                original_call_id = next(iter(self.pending_calls))

        created_by = self.pending_calls.pop(original_call_id, "assistant")

        short_id = self.short_call_id(original_call_id)
        output = content if isinstance(content, str) else json.dumps(content)
        is_error = message.get("error") is True

        self.items.append(
            FunctionCallOutput(
                id=short_id,
                call_id=short_id,
                output=output,
                status=FunctionCallOutputStatusEnum.incomplete
                if is_error
                else FunctionCallOutputStatusEnum.completed,
                original_call_id=original_call_id,
                created_by=created_by,
            )
        )

    def convert_tool_calls(self, tool_calls: list[dict[str, Any]], role: str) -> None:
        """Append ``FunctionCall`` items and register them as pending.

        Both user and assistant messages can carry tool calls.
        """
        for tool_call in tool_calls:
            arguments = tool_call["arguments"]
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments)

            original_call_id = tool_call["id"]
            short_id = self.short_call_id(original_call_id)
            self.pending_calls[original_call_id] = role

            self.items.append(
                FunctionCall(
                    id=short_id,
                    call_id=short_id,
                    name=tool_call["name"],
                    arguments=arguments,
                    status=FunctionCallStatus.completed,
                    original_call_id=original_call_id,
                    created_by=role,
                )
            )

    # ------------------------------------------------------------------
    # Main orchestrator
    # ------------------------------------------------------------------

    def convert(self, messages: list[dict[str, Any]]) -> list[TraceItem]:
        """Process all messages and return the list of TraceItems."""
        for message in messages:
            role = message["role"]
            content = message.get("content")
            tool_calls = message.get("tool_calls")

            if role == "user" and content is not None:
                self.convert_user_content(content)
            elif role == "assistant" and content is not None:
                self.convert_assistant_content(content)
            elif role == "tool":
                self.convert_tool_result(message)

            if tool_calls:
                self.convert_tool_calls(tool_calls, role)

        return self.items


def convert_simulation(simulation: dict[str, Any]) -> dict[str, Any]:
    """Convert a tau2bench simulation into a JSONL row dict."""
    converter = Tau2BenchMessageConverter()
    trace_items = converter.convert(simulation["messages"])
    trace = Trace.from_items(items=trace_items)

    return {
        "trace": trace.model_dump(mode="json"),
        "simulation_id": simulation["id"],
        "task_id": simulation["task_id"],
        "agent_cost": simulation.get("agent_cost", 0.0),
        "user_cost": simulation.get("user_cost", 0.0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a tau2bench JSON trace into a LatticeFlow AI GO dataset."
    )
    parser.add_argument(
        "--input-file", type=Path, required=True, help="Path to a tau2bench JSON file."
    )
    args = parser.parse_args()

    input_path = args.input_file
    if not input_path.is_file():
        raise SystemExit(f"Input file does not exist: {input_path}")

    stem = input_path.stem
    key = re.sub(r"[^a-zA-Z0-9_\-]", "-", stem)
    jsonl_path = Path(f"{key}.jsonl")
    yaml_path = Path(f"{key}.yaml")

    with open(input_path) as file:
        data = json.load(file)

    simulations = data["simulations"]
    print(f"Converting {input_path.name}: {len(simulations)} simulations")

    lines = [json.dumps(convert_simulation(sim)) for sim in simulations]
    jsonl_path.write_text("\n".join(lines) + "\n")

    dataset_spec = {
        "key": key,
        "display_name": stem,
        "source": {"type": "local", "file_path": f"./{key}.jsonl"},
    }
    with open(yaml_path, "w") as file:
        yaml.dump(dataset_spec, file, default_flow_style=False, sort_keys=False)

    print(f"  -> {jsonl_path} ({len(simulations)} rows)")
    print(f"  -> {yaml_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
