"""Sample-dependent scorer for tau2bench telecom traces.

Each dataset sample carries its own evaluation rules in the
``evaluation_criteria`` field.  This scorer reads those rules at runtime
and dynamically applies the matching checks.

Two scoring components
----------------------
1. **Action checks** — Were the expected tool calls found in the trace?
2. **Environment assertions** — Did the environment reach the expected
   final state?  Inferred from trace tool outputs (Status Bar text,
   function return values, etc.).

The final score is ``min(action_score, env_assertion_score)`` — both
components must pass for the sample to succeed.
"""

from __future__ import annotations

import json
from typing import Any


# ── Trace helpers ───────────────────────────────────────────────────────


def _extract_calls(trace: Any) -> list[dict[str, Any]]:
    """Extract function calls paired with their outputs from the trace."""
    outputs: dict[str, str] = {}
    for item in trace.items:
        if item.type == "function_call_output":
            outputs[item.call_id] = (
                item.output if isinstance(item.output, str) else str(item.output)
            )

    calls: list[dict[str, Any]] = []
    for item in trace.items:
        if item.type == "function_call":
            args = json.loads(item.arguments) if item.arguments else {}
            calls.append(
                {
                    "name": item.name,
                    "args": args,
                    "created_by": getattr(item, "created_by", "unknown"),
                    "output": outputs.get(item.call_id),
                }
            )
    return calls


def _last_status_bar(trace: Any) -> str | None:
    """Return the last Status Bar line from any tool output."""
    for item in reversed(list(trace.items)):
        if item.type == "function_call_output":
            text = item.output if isinstance(item.output, str) else str(item.output)
            if "Status Bar" in text:
                for line in text.split("\n"):
                    if "Status Bar" in line:
                        return line.strip()
    return None


def _last_tool_output(calls: list[dict], tool_name: str) -> str | None:
    """Return the output of the last call to *tool_name*."""
    for call in reversed(calls):
        if call["name"] == tool_name and call["output"] is not None:
            return call["output"]
    return None


# ── Action checks ──────────────────────────────────────────────────────


def _check_actions(expected: list[dict], calls: list[dict]) -> list[bool]:
    """Check each expected action against the trace.

    Matches by (function name, requestor/created_by).
    Arguments are NOT compared — only presence matters.
    """
    return [
        any(
            c["name"] == action["name"] and c["created_by"] == action["requestor"]
            for c in calls
        )
        for action in expected
    ]


# ── Environment assertion handlers ─────────────────────────────────────


def _assert_service_status(args: dict, status_bar: str | None,
                           calls: list[dict]) -> bool:
    expected = args["expected_status"]
    if status_bar is not None:
        has_signal = "\U0001f4f6" in status_bar          # 📶
        no_signal = "\U0001f4f5" in status_bar or "\u2708" in status_bar  # 📵 ✈
        return (has_signal and not no_signal) if expected == "connected" else (no_signal or not has_signal)
    # Fallback: if agent transferred, service was never fixed
    transferred = any(c["name"] == "transfer_to_human_agents" for c in calls)
    return (not transferred) if expected == "connected" else True


def _assert_mobile_data_status(args: dict, status_bar: str | None) -> bool:
    if status_bar is None:
        return False
    return ("Data Enabled" in status_bar) == args["expected_status"]


def _assert_internet_speed(args: dict, status_bar: str | None) -> bool:
    if status_bar is None:
        return False
    desc = args["expected_desc"]
    if desc == "excellent":
        return "\U0001f4f6\u2074" in status_bar and "5G" in status_bar and "Data Enabled" in status_bar
    if desc == "good":
        return "\U0001f4f6\u00b3" in status_bar
    return False


def _assert_can_send_mms(args: dict, calls: list[dict]) -> bool:
    """Check MMS capability using the can_send_mms tool output."""
    expected = args["expected_status"]
    output = _last_tool_output(calls, "can_send_mms")
    if output is None:
        return False  # no tool output available — conservative
    can_mms = "can send MMS" in output and "cannot" not in output
    return can_mms == expected


def _assert_no_overdue_bill(args: dict, calls: list[dict],
                            broken: set[str]) -> bool:
    """Cross-reference initial state with trace actions."""
    if "suspend_line_for_overdue_bill" not in broken:
        return True  # bill was never overdue
    return any(c["name"] == "make_payment" for c in calls)


def _assert_data_refueling_amount(args: dict, calls: list[dict]) -> bool:
    """Check that refuel_data was called with the expected arguments."""
    return any(
        c["name"] == "refuel_data"
        and c["args"].get("customer_id") == args["customer_id"]
        and c["args"].get("line_id") == args["line_id"]
        and c["args"].get("gb_amount") == args["expected_amount"]
        for c in calls
    )


# Dispatch table: assertion func_name → handler
_HANDLERS = {
    "assert_service_status":        lambda a, sb, calls, broken: _assert_service_status(a, sb, calls),
    "assert_mobile_data_status":    lambda a, sb, calls, broken: _assert_mobile_data_status(a, sb),
    "assert_internet_speed":        lambda a, sb, calls, broken: _assert_internet_speed(a, sb),
    "assert_can_send_mms":          lambda a, sb, calls, broken: _assert_can_send_mms(a, calls),
    "assert_no_overdue_bill":       lambda a, sb, calls, broken: _assert_no_overdue_bill(a, calls, broken),
    "assert_data_refueling_amount": lambda a, sb, calls, broken: _assert_data_refueling_amount(a, calls),
}


def _check_env_assertions(assertions: list[dict], trace: Any,
                           calls: list[dict], init_actions: list[dict]) -> list[bool]:
    """Evaluate each environment assertion by dispatching to its handler."""
    status_bar = _last_status_bar(trace)
    broken = {a["func_name"] for a in init_actions}
    results = []
    for assertion in assertions:
        handler = _HANDLERS.get(assertion["func_name"])
        if handler is None:
            results.append(False)  # unknown assertion — conservative
            continue
        met = handler(assertion["arguments"], status_bar, calls, broken)
        # Flip if assert_value is False (rare, but supported)
        results.append(met == assertion.get("assert_value", True))
    return results


# ── Entry point ────────────────────────────────────────────────────────


def compute_scores(sample: dict[str, Any], solver_output: Any) -> dict[str, Any]:
    """Score a tau2bench trace against its per-sample evaluation criteria.

    Called once for each dataset sample by the AI GO! platform.
    """
    trace = solver_output.trace
    criteria = sample["evaluation_criteria"]
    init_actions = sample["initial_state"]["initialization_actions"]

    # Handle empty traces (e.g. infrastructure errors)
    if not trace.items:
        return {"score": 0.0, "action_score": 0.0, "env_assertion_score": 0.0,
                "action_coverage": 0.0, "empty_trace": True}

    calls = _extract_calls(trace)

    # 1. Action checks
    action_results = _check_actions(criteria.get("actions", []), calls)
    action_score = 1.0 if all(action_results) else 0.0 if action_results else 1.0
    action_coverage = sum(action_results) / len(action_results) if action_results else 1.0

    # 2. Environment assertions
    env_results = _check_env_assertions(
        criteria.get("env_assertions", []), trace, calls, init_actions,
    )
    env_score = 1.0 if all(env_results) else 0.0 if env_results else 1.0

    # 3. Combine: both components must pass
    score = min(action_score, env_score)

    return {
        "score": score,
        "action_score": action_score,
        "env_assertion_score": env_score,
        "action_coverage": action_coverage,
    }
