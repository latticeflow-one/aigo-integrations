#!/usr/bin/env python3
"""Select and simplify samples from the GPT-5.2 None tau2bench dataset.

Produces a curated tutorial dataset with ~20 samples covering all 6 assertion
types and a mix of passing/failing traces.

Usage:
    python select_samples.py
"""

import json
from collections import defaultdict
from pathlib import Path

SOURCE = Path(__file__).parent.parent / "datasets" / "gpt-5-2_none_telecom_gpt-5-2_4trials.jsonl"
OUTPUT = Path(__file__).parent / "datasets" / "tutorial-samples.jsonl"

# ── Assertion combo groups we want represented ──────────────────────────

SELECTION = {
    # combo → (desired_pass, desired_fail)
    ("assert_service_status",): (2, 2),
    ("assert_no_overdue_bill", "assert_service_status"): (2, 2),
    ("assert_internet_speed", "assert_mobile_data_status"): (2, 1),
    ("assert_data_refueling_amount", "assert_internet_speed", "assert_mobile_data_status"): (1, 1),
    ("assert_can_send_mms",): (1, 1),
    ("assert_can_send_mms", "assert_data_refueling_amount"): (1, 1),
}


def simplify_sample(raw: dict) -> dict:
    """Strip a raw tau2bench sample down to tutorial-relevant fields."""
    ec = raw["task_metadata"]["evaluation_criteria"]
    init_state = raw["task_metadata"].get("initial_state", {})
    return {
        "task_id": raw["task_id"],
        "trace": raw["trace"],
        "evaluation_criteria": {
            "actions": [
                {"name": a["name"], "requestor": a["requestor"]}
                for a in ec["actions"]
            ],
            "env_assertions": [
                {
                    "func_name": a["func_name"],
                    "arguments": a["arguments"],
                    "assert_value": a["assert_value"],
                }
                for a in ec["env_assertions"]
            ],
        },
        "initial_state": {
            "initialization_actions": [
                {"func_name": a["func_name"], "arguments": a.get("arguments", {})}
                for a in init_state.get("initialization_actions", [])
            ],
        },
    }


def main():
    with open(SOURCE) as f:
        all_samples = [json.loads(line) for line in f]

    # Index by (assertion_combo, pass/fail) using trial 0 only for consistency
    by_combo = defaultdict(lambda: {"pass": [], "fail": []})
    for s in all_samples:
        if s["trial"] != 0:
            continue
        ec = s["task_metadata"]["evaluation_criteria"]
        combo = tuple(sorted(a["func_name"] for a in ec["env_assertions"]))
        reward = (s.get("reward_info") or {}).get("reward", 0.0)
        bucket = "pass" if reward == 1.0 else "fail"
        by_combo[combo][bucket].append(s)

    selected = []
    for combo, (want_pass, want_fail) in SELECTION.items():
        pool = by_combo.get(combo, {"pass": [], "fail": []})
        passing = pool["pass"][:want_pass]
        failing = pool["fail"][:want_fail]
        selected.extend(passing)
        selected.extend(failing)
        print(
            f"{str(combo):85s}  "
            f"picked {len(passing)}P + {len(failing)}F "
            f"(avail {len(pool['pass'])}P + {len(pool['fail'])}F)"
        )

    # Simplify and write
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        for s in selected:
            f.write(json.dumps(simplify_sample(s)) + "\n")

    print(f"\nWrote {len(selected)} samples to {OUTPUT}")

    # Summary
    all_assertions = set()
    for s in selected:
        simplified = simplify_sample(s)
        for a in simplified["evaluation_criteria"]["env_assertions"]:
            all_assertions.add(a["func_name"])
    print(f"Assertion types covered: {sorted(all_assertions)}")


if __name__ == "__main__":
    main()
