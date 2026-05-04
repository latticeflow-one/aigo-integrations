"""Convert tau2bench JSON trace files into LatticeFlow AI GO datasets.

Reads tau2bench simulation JSONs from --input-dir, writes per-file .jsonl
datasets and matching dataset YAML specs to --output-dir.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

import yaml

from latticeflow.assessment.dtypes import AssistantMessage
from latticeflow.assessment.dtypes import SYNTHETIC_MESSAGE_STATUS
from latticeflow.assessment.dtypes import Trace
from latticeflow.assessment.dtypes import TraceItem as TraceItemType
from latticeflow.assessment.dtypes import UserMessage
from latticeflow.bindings.open_responses.models import FunctionCall
from latticeflow.bindings.open_responses.models import FunctionCallOutput
from latticeflow.bindings.open_responses.models import FunctionCallOutputStatusEnum
from latticeflow.bindings.open_responses.models import FunctionCallStatus
from latticeflow.bindings.open_responses.models import InputTextContent
from latticeflow.bindings.open_responses.models import OutputTextContent


def _sanitize_key(name: str) -> str:
    """Sanitize a filename into a valid AI GO entity key (``[a-zA-Z0-9_-]``)."""
    import re

    return re.sub(r"[^a-zA-Z0-9_\-]", "-", name)


def _short_call_id(call_id: str) -> str:
    """Hash a long call_id to a 12-char hex string."""
    return hashlib.sha256(call_id.encode()).hexdigest()[:12]


def convert_messages(messages: list[dict[str, Any]]) -> list[TraceItemType]:
    """Convert tau2bench messages into LF TraceItems.

    Processes messages sequentially. Tool results are matched to preceding
    FunctionCalls via a queue of pending call_ids, because some providers
    (e.g. Gemini) omit the ``id`` field on tool result messages.
    """
    items: list[TraceItemType] = []
    # Maps original_call_id -> role that requested the call, consumed by tool results.
    pending_calls: dict[str, str] = {}

    for message in messages:
        role = message["role"]
        content = message.get("content")
        tool_calls = message.get("tool_calls")

        if role == "user":
            if content is not None:
                items.append(
                    UserMessage(
                        id=str(uuid.uuid4()),
                        status=SYNTHETIC_MESSAGE_STATUS,
                        content=[InputTextContent(text=content)],
                    )
                )

        elif role == "assistant":
            if content is not None:
                items.append(
                    AssistantMessage(
                        id=str(uuid.uuid4()),
                        status=SYNTHETIC_MESSAGE_STATUS,
                        content=[OutputTextContent(text=content, annotations=[])],
                    )
                )

        elif role == "tool":
            # Prefer explicit id; fall back to pending queue from preceding FunctionCalls.
            original_call_id = message.get("id")
            if original_call_id is None:
                if not pending_calls:
                    original_call_id = str(uuid.uuid4())
                else:
                    # Pop the oldest pending call (FIFO).
                    original_call_id = next(iter(pending_calls))
            created_by = pending_calls.pop(original_call_id, "assistant")

            short_id = _short_call_id(original_call_id)
            output = content if isinstance(content, str) else json.dumps(content)
            is_error = message.get("error") is True
            items.append(
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

        # Emit FunctionCall items for both user and assistant tool calls.
        if tool_calls:
            for tool_call in tool_calls:
                arguments = tool_call["arguments"]
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments)
                original_call_id = tool_call["id"]
                short_id = _short_call_id(original_call_id)
                pending_calls[original_call_id] = role
                items.append(
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

    return items


def _build_task_lookup(tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build a task_id -> task metadata dict, excluding the ``id`` field."""
    lookup: dict[str, dict[str, Any]] = {}
    for task in tasks:
        metadata = {k: v for k, v in task.items() if k != "id"}
        lookup[task["id"]] = metadata
    return lookup


def convert_simulation(
    simulation: dict[str, Any],
    task_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Convert a tau2bench simulation into a JSONL row dict."""
    trace_items = convert_messages(simulation["messages"])
    trace = Trace.from_items(items=trace_items)

    task_id = simulation["task_id"]
    task_metadata = task_lookup.get(task_id)

    return {
        "trace": trace.model_dump(mode="json"),
        "simulation_id": simulation["id"],
        "task_id": task_id,
        "trial": simulation["trial"],
        "task_metadata": task_metadata,
        "reward_info": simulation.get("reward_info"),
        "agent_cost": simulation.get("agent_cost"),
        "user_cost": simulation.get("user_cost"),
        "seed": simulation.get("seed"),
        "termination_reason": simulation["termination_reason"],
        "duration": simulation["duration"],
    }


def convert_file(input_path: Path, output_dir: Path) -> None:
    """Convert one tau2bench JSON file into a .jsonl dataset and .yaml spec."""
    stem = input_path.stem
    key = _sanitize_key(stem)
    jsonl_path = output_dir / f"{key}.jsonl"
    yaml_path = output_dir / f"{key}.yaml"

    with open(input_path) as file:
        data = json.load(file)

    simulations = data["simulations"]
    task_lookup = _build_task_lookup(data.get("tasks", []))
    print(f"Converting {input_path.name}: {len(simulations)} simulations, {len(task_lookup)} tasks")

    with open(jsonl_path, "w") as file:
        for simulation in simulations:
            row = convert_simulation(simulation, task_lookup)
            file.write(json.dumps(row) + "\n")

    dataset_spec = {
        "key": key,
        "display_name": stem,
        "source": {"type": "local", "file_path": f"./{key}.jsonl"},
    }
    with open(yaml_path, "w") as file:
        yaml.dump(dataset_spec, file, default_flow_style=False, sort_keys=False)

    print(f"  -> {jsonl_path.name} ({len(simulations)} rows)")
    print(f"  -> {yaml_path.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert tau2bench JSON traces into LatticeFlow AI GO datasets."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing tau2bench JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("datasets"),
        help="Output directory for .jsonl and .yaml files (default: ./datasets).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        raise SystemExit(f"No JSON files found in {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(json_files)} JSON files in {input_dir}")
    print(f"Output directory: {output_dir}")
    print()

    for json_file in json_files:
        convert_file(json_file, output_dir)
        print()

    print("Done.")


if __name__ == "__main__":
    main()
