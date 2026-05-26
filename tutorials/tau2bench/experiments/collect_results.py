"""Convert tau2bench results to AI GO! format and upload.

Reads tau2bench results.json, converts traces to LatticeFlow Open Responses
format, writes JSONL dataset + YAML spec, and optionally runs lf add + lf run.

Usage:
    # Convert only (inspect before uploading)
    python collect_results.py --input results/results.json --name hypothesis-pilot-gpt52

    # Convert and upload to AI GO!
    python collect_results.py --input results/results.json --name hypothesis-pilot-gpt52 --upload

    # Convert, upload, and run evaluation
    python collect_results.py --input results/results.json --name hypothesis-pilot-gpt52 --upload --run-eval
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any

import yaml

from latticeflow.core.dtypes import (
    AssistantMessage,
    FunctionCall,
    FunctionCallOutput,
    Trace,
    UserMessage,
)
from latticeflow.core.dtypes._open_responses.models import (
    FunctionCallOutputStatusEnum,
    FunctionCallStatus,
    InputTextContent,
    MessageStatus,
    OutputTextContent,
)

# Status constant matching the existing datasets' convention.
_STATUS = MessageStatus.completed


def _short_call_id(call_id: str) -> str:
    """Hash a long call_id to a 12-char hex string."""
    return hashlib.sha256(call_id.encode()).hexdigest()[:12]


def convert_messages(messages: list[dict[str, Any]]) -> list:
    """Convert tau2bench messages into LF TraceItems.

    Mirrors the logic from convert_tau2bench.py but uses current SDK imports.
    Preserves ``created_by`` on FunctionCall/FunctionCallOutput items, which
    the scorer uses to distinguish agent vs user tool calls.
    """
    items = []
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
                        status=_STATUS,
                        content=[InputTextContent(text=content)],
                    )
                )
        elif role == "assistant":
            if content is not None:
                items.append(
                    AssistantMessage(
                        id=str(uuid.uuid4()),
                        status=_STATUS,
                        content=[OutputTextContent(text=content, annotations=[])],
                    )
                )
        elif role == "tool":
            original_call_id = message.get("id")
            if original_call_id is None:
                if not pending_calls:
                    original_call_id = str(uuid.uuid4())
                else:
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


def _sanitize_key(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "-", name)


def convert_simulation(
    simulation: dict[str, Any],
    task_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Convert a single tau2bench simulation into a JSONL row."""
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


def convert_results(input_path: Path, name: str, output_dir: Path) -> tuple[Path, Path]:
    """Convert tau2bench results.json to JSONL dataset + YAML spec."""
    with open(input_path) as f:
        data = json.load(f)

    simulations = data["simulations"]
    task_lookup = {}
    for task in data.get("tasks", []):
        metadata = {k: v for k, v in task.items() if k != "id"}
        task_lookup[task["id"]] = metadata

    key = _sanitize_key(name)
    jsonl_path = output_dir / f"{key}.jsonl"
    yaml_path = output_dir / f"{key}.yaml"

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(jsonl_path, "w") as f:
        for sim in simulations:
            row = convert_simulation(sim, task_lookup)
            f.write(json.dumps(row) + "\n")

    dataset_spec = {
        "key": key,
        "display_name": name,
        "source": {"type": "local", "file_path": f"./{key}.jsonl"},
    }
    with open(yaml_path, "w") as f:
        yaml.dump(dataset_spec, f, default_flow_style=False, sort_keys=False)

    print(f"Converted {len(simulations)} simulations -> {jsonl_path.name}")

    # Print summary
    rewards = [s.get("reward_info", {}).get("reward", 0) for s in simulations if s.get("reward_info")]
    if rewards:
        pass_rate = sum(1 for r in rewards if r == 1.0) / len(rewards)
        print(f"  tau2bench reward: {sum(rewards)}/{len(rewards)} pass ({pass_rate:.1%})")

    return jsonl_path, yaml_path


def upload_dataset(yaml_path: Path, output_dir: Path):
    """Upload dataset to AI GO! via lf add."""
    cmd = ["lf", "add", "dataset", "-f", str(yaml_path)]
    print(f"\nRunning: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(output_dir), check=True)


def run_evaluation(dataset_key: str, run_yaml_dir: Path):
    """Create and run an evaluation with the existing tau2bench scorer task."""
    run_spec = {
        "datasets": [{"key": dataset_key, "display_name": dataset_key}],
        "evaluation": {
            "key": f"hypothesis-eval-{dataset_key}",
            "display_name": f"Hypothesis Test: {dataset_key}",
            "task_specifications": [
                {
                    "task_key": "tau2bench-telecom-eval",
                    "model_key": "openai$gpt-4-1-nano",
                    "task_config": {
                        "eval_dataset": dataset_key,
                    },
                }
            ],
        },
    }

    run_path = run_yaml_dir / f"run_{dataset_key}.yaml"
    with open(run_path, "w") as f:
        yaml.dump(run_spec, f, default_flow_style=False, sort_keys=False)

    # Validate first
    cmd_validate = ["lf", "run", "-f", str(run_path), "-v"]
    print(f"\nValidating: {' '.join(cmd_validate)}")
    result = subprocess.run(cmd_validate, cwd=str(run_yaml_dir))
    if result.returncode != 0:
        print("Validation failed. Fix issues before running.")
        return

    # Run
    cmd_run = ["lf", "run", "-f", str(run_path), "-w"]
    print(f"Running: {' '.join(cmd_run)}")
    subprocess.run(cmd_run, cwd=str(run_yaml_dir), check=True)


def main():
    parser = argparse.ArgumentParser(description="Convert tau2bench results to AI GO!")
    parser.add_argument(
        "--input", type=Path, required=True,
        help="Path to tau2bench results.json",
    )
    parser.add_argument(
        "--name", type=str, required=True,
        help="Dataset name / key (e.g., hypothesis-pilot-gpt52-none)",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path(__file__).parent / "datasets",
        help="Output directory for JSONL + YAML (default: datasets/)",
    )
    parser.add_argument(
        "--upload", action="store_true",
        help="Upload dataset to AI GO! after conversion",
    )
    parser.add_argument(
        "--run-eval", action="store_true",
        help="Run evaluation after uploading (implies --upload)",
    )
    args = parser.parse_args()

    if args.run_eval:
        args.upload = True

    jsonl_path, yaml_path = convert_results(args.input, args.name, args.output_dir)

    if args.upload:
        upload_dataset(yaml_path, args.output_dir)

    if args.run_eval:
        dataset_key = _sanitize_key(args.name)
        run_evaluation(dataset_key, args.output_dir)


if __name__ == "__main__":
    main()
