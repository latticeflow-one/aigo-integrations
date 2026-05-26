"""Generate targeted hypothesis-test scenarios using tau2bench internals.

Uses tau2bench's task generation machinery to create controlled experiments:
  H1: MMS fault isolation (single-fault + pairwise)
  H3: Hard user actions (action-count ladder)

Usage:
    # Must run with tau2bench's uv environment
    python generate_scenarios.py [--full]

    Without --full: generates a small pilot set (~8 tasks) for pipeline validation.
    With --full: generates the complete hypothesis test set (~43 tasks).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# --- tau2bench imports (requires tau2bench venv) ---
from tau2.domains.telecom.tasks.mms_issues import (
    bad_wifi_calling_task,
    break_apn_mms_setting_task,
    break_app_both_permissions_task,
    break_app_sms_permission_task,
    break_app_storage_permission_task,
    mms_issue_task_manager,
    selection_sets as mms_selection_sets,
)
from tau2.domains.telecom.tasks.mobile_data_issues import (
    bad_network_preference_task,
    data_mode_off_task,
    data_usage_exceeded_task,
)
from tau2.domains.telecom.tasks.service_issues import (
    airplane_mode_on_task,
    unseat_sim_card_task,
)
from tau2.domains.telecom.tasks.utils import ComposedTask

# ---------------------------------------------------------------------------
# All MMS-relevant BaseTask objects, keyed by fault name.
# Sets 0-4 are inherited from service/mobile_data; sets 5-8 are MMS-specific.
# ---------------------------------------------------------------------------
ALL_MMS_FAULTS = {
    # Inherited faults (also used in MMS scenarios)
    "airplane_mode_on": airplane_mode_on_task,
    "unseat_sim_card": unseat_sim_card_task,
    "data_mode_off": data_mode_off_task,
    "data_usage_exceeded": data_usage_exceeded_task,
    # MMS-specific faults
    "bad_network_preference": bad_network_preference_task,
    "bad_wifi_calling": bad_wifi_calling_task,
    "break_apn_mms_setting": break_apn_mms_setting_task,
    "break_app_sms_permission": break_app_sms_permission_task,
    "break_app_storage_permission": break_app_storage_permission_task,
    "break_app_both_permissions": break_app_both_permissions_task,
}

# Hypothesized "hard" actions: the user-side resolution steps that we suspect
# are difficult for agents to guide.  Selected from risk analysis findings.
HARD_ACTION_FAULTS = [
    "break_apn_mms_setting",       # requires: reset_apn_settings + reboot_device (2 steps)
    "break_app_both_permissions",   # requires: grant_app_permission x2 (2 steps)
    "bad_wifi_calling",             # requires: toggle_wifi_calling (1 step, uncommon action)
]

# "Easy" baseline faults (common actions agents should handle well)
EASY_ACTION_FAULTS = [
    "airplane_mode_on",            # requires: toggle_airplane_mode (1 step, standard)
    "data_mode_off",               # requires: toggle_data (1 step, standard)
]


def _make_composed(fault_names: list[str]) -> ComposedTask:
    """Build a ComposedTask from a list of fault names."""
    tasks = sorted(
        [ALL_MMS_FAULTS[name] for name in fault_names],
        key=lambda t: t.name,
    )
    return ComposedTask(
        name="|".join(t.name for t in tasks),
        description=", ".join(t.description for t in tasks),
        composed_from=tasks,
        init_funcs=[f for t in tasks for f in t.init_funcs],
        fix_funcs=[f for t in tasks for f in t.fix_funcs],
        extra_env_assertions=[f for t in tasks for f in t.extra_env_assertions],
    )


def _create_task(fault_names: list[str], persona: str = "None"):
    """Create a tau2bench Task from a list of fault names."""
    composed = _make_composed(fault_names)
    return mms_issue_task_manager.create_task(composed, persona=persona)


def generate_pilot() -> list[dict]:
    """Generate a small pilot set for pipeline validation (~8 tasks).

    Covers:
      - 3 single-fault MMS (1 easy + 2 hard)
      - 2 pairwise (1 easy+hard, 1 hard+hard)
      - 1 triple-fault (action count = 4-5)
    """
    scenarios = []

    # --- H1: Single-fault isolation ---
    # Easy baseline
    scenarios.append(("H1_single", ["airplane_mode_on"]))
    # Hard faults
    scenarios.append(("H1_single", ["break_apn_mms_setting"]))
    scenarios.append(("H1_single", ["break_app_both_permissions"]))

    # --- H1: Pairwise combinations ---
    scenarios.append(("H1_pair", ["airplane_mode_on", "break_apn_mms_setting"]))
    scenarios.append(("H1_pair", ["bad_wifi_calling", "break_app_both_permissions"]))

    # --- H3: Action-count ladder ---
    # 3 faults -> many required actions
    scenarios.append(("H3_ladder", ["airplane_mode_on", "break_apn_mms_setting", "bad_wifi_calling"]))
    # 4 faults -> even more actions
    scenarios.append(("H3_ladder", ["airplane_mode_on", "data_mode_off", "break_apn_mms_setting", "bad_wifi_calling"]))
    # 5 faults
    scenarios.append(("H3_ladder", ["airplane_mode_on", "data_mode_off", "break_apn_mms_setting", "bad_wifi_calling", "break_app_both_permissions"]))

    tasks = []
    for tag, faults in scenarios:
        task = _create_task(faults)
        task_dict = task.model_dump(mode="json")
        task_dict["_hypothesis_tag"] = tag
        task_dict["_fault_names"] = sorted(faults)
        task_dict["_num_faults"] = len(faults)
        tasks.append(task_dict)

    return tasks


def generate_full() -> list[dict]:
    """Generate the complete hypothesis test set.

    H1: All single-fault MMS (10 tasks) + top pairwise combos (~15 tasks)
    H3: Action-count ladder (variable fault count, ~10 tasks) + hard-action isolation (~5 tasks)
    """
    tasks = []

    # --- H1: ALL single-fault MMS ---
    for fault_name in sorted(ALL_MMS_FAULTS.keys()):
        task = _create_task([fault_name])
        task_dict = task.model_dump(mode="json")
        task_dict["_hypothesis_tag"] = "H1_single"
        task_dict["_fault_names"] = [fault_name]
        task_dict["_num_faults"] = 1
        tasks.append(task_dict)

    # --- H1: Pairwise combinations of top-6 faults ---
    top6 = [
        "airplane_mode_on",
        "data_mode_off",
        "data_usage_exceeded",
        "bad_network_preference",
        "break_apn_mms_setting",
        "break_app_both_permissions",
    ]
    for i, f1 in enumerate(top6):
        for f2 in top6[i + 1 :]:
            task = _create_task([f1, f2])
            task_dict = task.model_dump(mode="json")
            task_dict["_hypothesis_tag"] = "H1_pair"
            task_dict["_fault_names"] = sorted([f1, f2])
            task_dict["_num_faults"] = 2
            tasks.append(task_dict)

    # --- H3: Action-count ladder ---
    # Build scenarios with 1, 2, 3, 4, 5 required user actions
    # by combining faults of known action counts.
    ladder = [
        # 1 action
        ["airplane_mode_on"],
        ["data_mode_off"],
        # 2 actions (break_apn needs reset_apn + reboot)
        ["break_apn_mms_setting"],
        ["airplane_mode_on", "data_mode_off"],
        # 3 actions
        ["airplane_mode_on", "break_apn_mms_setting"],
        ["airplane_mode_on", "data_mode_off", "bad_network_preference"],
        # 4 actions
        ["airplane_mode_on", "data_mode_off", "break_apn_mms_setting"],
        ["airplane_mode_on", "bad_wifi_calling", "break_app_both_permissions"],
        # 5+ actions
        ["airplane_mode_on", "data_mode_off", "break_apn_mms_setting", "bad_wifi_calling"],
        ["airplane_mode_on", "data_mode_off", "break_apn_mms_setting", "bad_wifi_calling", "break_app_both_permissions"],
    ]
    for faults in ladder:
        task = _create_task(faults)
        task_dict = task.model_dump(mode="json")
        # Count actual required actions
        num_actions = len(task.evaluation_criteria.actions)
        task_dict["_hypothesis_tag"] = "H3_ladder"
        task_dict["_fault_names"] = sorted(faults)
        task_dict["_num_faults"] = len(faults)
        task_dict["_num_required_actions"] = num_actions
        tasks.append(task_dict)

    # --- H3: Hard-action isolation ---
    for fault_name in HARD_ACTION_FAULTS:
        task = _create_task([fault_name])
        task_dict = task.model_dump(mode="json")
        task_dict["_hypothesis_tag"] = "H3_hard_action"
        task_dict["_fault_names"] = [fault_name]
        task_dict["_num_faults"] = 1
        tasks.append(task_dict)

    # Deduplicate by task ID (some ladder tasks overlap with H1 singles)
    seen_ids = set()
    deduped = []
    for t in tasks:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            deduped.append(t)

    return deduped


def main():
    parser = argparse.ArgumentParser(description="Generate hypothesis-test scenarios")
    parser.add_argument(
        "--full", action="store_true",
        help="Generate complete hypothesis set (default: pilot only)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).parent / "tasks",
        help="Output directory for tasks JSON",
    )
    args = parser.parse_args()

    if args.full:
        tasks = generate_full()
        filename = "hypothesis_full.json"
    else:
        tasks = generate_pilot()
        filename = "hypothesis_pilot.json"

    output_path = args.output_dir / filename
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(tasks, f, indent=2)

    # Print summary
    print(f"Generated {len(tasks)} tasks -> {output_path}")
    print()
    tags = {}
    for t in tasks:
        tag = t.get("_hypothesis_tag", "unknown")
        tags[tag] = tags.get(tag, 0) + 1
    for tag, count in sorted(tags.items()):
        print(f"  {tag}: {count} tasks")
    print()
    for t in tasks:
        num_actions = len(t["evaluation_criteria"]["actions"])
        faults = t.get("_fault_names", [])
        print(f"  {t['id']}")
        print(f"    faults={faults}, actions={num_actions}, tag={t.get('_hypothesis_tag')}")


if __name__ == "__main__":
    main()
