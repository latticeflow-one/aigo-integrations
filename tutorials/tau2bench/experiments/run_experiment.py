"""Inject custom tasks into tau2bench and run experiments.

Temporarily patches the telecom tasks.json and split_tasks.json in the
tau2bench repo, runs the simulation, then restores the original files.

Usage:
    # Must run with tau2bench's uv environment
    python run_experiment.py --tasks tasks/hypothesis_pilot.json \
        --agent-llm gpt-5.2 \
        --agent-llm-args '{"reasoning_effort":"none"}' \
        --save-to hypothesis_pilot_gpt52_none

    # Dry-run: inject tasks but don't run (verify task injection)
    python run_experiment.py --tasks tasks/hypothesis_pilot.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

TAU2_REPO = Path.home() / "workspace" / "tau2-bench"
TAU2_DATA = TAU2_REPO / "data" / "tau2" / "domains" / "telecom"
TASKS_JSON = TAU2_DATA / "tasks.json"
SPLIT_JSON = TAU2_DATA / "split_tasks.json"
RESULTS_DIR = TAU2_REPO / "data" / "simulations"

SPLIT_NAME = "hypothesis_test"


def inject_tasks(custom_tasks: list[dict]) -> tuple[Path, Path]:
    """Append custom tasks to tasks.json and register a split.

    Returns paths to the backup files for restoration.
    """
    # Backup originals
    tasks_backup = TASKS_JSON.with_suffix(".json.bak")
    split_backup = SPLIT_JSON.with_suffix(".json.bak")
    shutil.copy2(TASKS_JSON, tasks_backup)
    shutil.copy2(SPLIT_JSON, split_backup)

    # Strip our metadata fields before injecting
    clean_tasks = []
    for t in custom_tasks:
        clean = {k: v for k, v in t.items() if not k.startswith("_")}
        clean_tasks.append(clean)

    # Load existing tasks and append
    with open(TASKS_JSON) as f:
        existing = json.load(f)

    existing_ids = {t["id"] for t in existing}
    added = 0
    for t in clean_tasks:
        if t["id"] not in existing_ids:
            existing.append(t)
            added += 1

    with open(TASKS_JSON, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"Injected {added} tasks into {TASKS_JSON} ({len(existing)} total)")

    # Register split
    with open(SPLIT_JSON) as f:
        splits = json.load(f)

    custom_ids = [t["id"] for t in clean_tasks]
    splits[SPLIT_NAME] = custom_ids

    with open(SPLIT_JSON, "w") as f:
        json.dump(splits, f, indent=2)
    print(f"Registered split '{SPLIT_NAME}' with {len(custom_ids)} task IDs")

    return tasks_backup, split_backup


def restore_files(tasks_backup: Path, split_backup: Path):
    """Restore original tasks.json and split_tasks.json from backups."""
    shutil.move(str(tasks_backup), str(TASKS_JSON))
    shutil.move(str(split_backup), str(SPLIT_JSON))
    print("Restored original tasks.json and split_tasks.json")


def run_tau2(
    save_to: str,
    agent_llm: str,
    agent_llm_args: str,
    user_llm: str,
    user_llm_args: str,
    num_trials: int,
    max_concurrency: int,
) -> Path:
    """Run tau2bench with the injected tasks."""
    cmd = [
        sys.executable, "-m", "tau2.cli", "run",
        "--domain", "telecom",
        "--task-split-name", SPLIT_NAME,
        "--agent-llm", agent_llm,
        "--agent-llm-args", agent_llm_args,
        "--user-llm", user_llm,
        "--user-llm-args", user_llm_args,
        "--num-trials", str(num_trials),
        "--max-concurrency", str(max_concurrency),
        "--save-to", save_to,
        "--seed", "300",
    ]
    print(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(TAU2_REPO))

    results_path = RESULTS_DIR / save_to / "results.json"
    if result.returncode != 0:
        print(f"\ntau2 run failed with exit code {result.returncode}")
    elif results_path.exists():
        print(f"\nResults saved to {results_path}")
    else:
        print(f"\nRun completed but results not found at {results_path}")

    return results_path


def copy_results(results_path: Path, output_dir: Path):
    """Copy results to our experiments directory."""
    if results_path.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / results_path.name
        shutil.copy2(results_path, dest)
        print(f"Copied results to {dest}")
    else:
        print(f"Warning: results file not found at {results_path}")


def main():
    parser = argparse.ArgumentParser(description="Run tau2bench hypothesis experiments")
    parser.add_argument(
        "--tasks", type=Path, required=True,
        help="Path to custom tasks JSON (e.g., tasks/hypothesis_pilot.json)",
    )
    parser.add_argument(
        "--save-to", type=str, required=True,
        help="Name for tau2bench results directory",
    )
    parser.add_argument(
        "--agent-llm", type=str, default="gpt-5.2",
        help="Agent LLM model string (default: gpt-5.2)",
    )
    parser.add_argument(
        "--agent-llm-args", type=str, default='{"reasoning_effort":"none"}',
        help="Agent LLM args as JSON string",
    )
    parser.add_argument(
        "--user-llm", type=str, default="gpt-5.2",
        help="User simulator LLM (default: gpt-5.2)",
    )
    parser.add_argument(
        "--user-llm-args", type=str, default='{"reasoning_effort":"low"}',
        help="User simulator LLM args as JSON string",
    )
    parser.add_argument(
        "--num-trials", type=int, default=1,
        help="Trials per task (default: 1)",
    )
    parser.add_argument(
        "--max-concurrency", type=int, default=3,
        help="Max concurrent simulations (default: 3)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Inject tasks and print config but don't run",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path(__file__).parent / "results",
        help="Local directory to copy results to",
    )
    args = parser.parse_args()

    # Load custom tasks
    with open(args.tasks) as f:
        custom_tasks = json.load(f)
    print(f"Loaded {len(custom_tasks)} tasks from {args.tasks}")

    # Inject into tau2bench
    tasks_backup, split_backup = inject_tasks(custom_tasks)

    try:
        if args.dry_run:
            print("\n[DRY RUN] Tasks injected. Inspect tau2bench files:")
            print(f"  tasks.json: {TASKS_JSON}")
            print(f"  split_tasks.json: {SPLIT_JSON}")
            print(f"\nWould run: tau2 run -d telecom --task-split-name {SPLIT_NAME}")
            print(f"  --agent-llm {args.agent_llm}")
            print(f"  --agent-llm-args '{args.agent_llm_args}'")
            print(f"  --user-llm {args.user_llm}")
            print(f"  --num-trials {args.num_trials}")
            print(f"  --save-to {args.save_to}")
            input("\nPress Enter to restore original files...")
        else:
            results_path = run_tau2(
                save_to=args.save_to,
                agent_llm=args.agent_llm,
                agent_llm_args=args.agent_llm_args,
                user_llm=args.user_llm,
                user_llm_args=args.user_llm_args,
                num_trials=args.num_trials,
                max_concurrency=args.max_concurrency,
            )
            copy_results(results_path, args.output_dir)
    finally:
        restore_files(tasks_backup, split_backup)


if __name__ == "__main__":
    main()
