"""Tau2Bench telecom scorer — replicates tau2bench reward logic from traces.

Receives a pre-recorded Open Responses trace via the pass-through solver and
evaluates it against the evaluation criteria stored in the dataset sample.

Scoring components
------------------
1. **Action checks** — Did the expected tool calls appear in the trace?
   Matched by function name + created_by (requestor).
2. **Environment assertions** — Did the environment reach the expected final
   state? Inferred from trace tool outputs (status bar, can_send_mms, etc.)
   with fallbacks when direct tool outputs are unavailable.

The final reward is ``min(score per basis component)`` following the
``reward_basis`` list in the evaluation criteria. Each component is binary:
1.0 if ALL sub-checks pass, 0.0 otherwise.
"""

from __future__ import annotations

import json
import math
from typing import Any


def _safe_get_reward(reward_info: Any) -> float | None:
    """Extract the reward value from reward_info, handling nan/None/non-dict."""
    if reward_info is None:
        return None
    if isinstance(reward_info, (int, float)):
        return None if math.isnan(reward_info) else float(reward_info)
    if isinstance(reward_info, dict):
        val = reward_info.get("reward")
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None
        return float(val)
    return None


# ---------------------------------------------------------------------------
# Trace helpers
# ---------------------------------------------------------------------------

def _extract_function_calls(trace: Any) -> list[dict[str, Any]]:
    """Extract function calls with their matched outputs from the trace.

    Returns a list of dicts with keys: name, arguments (parsed dict),
    call_id, created_by, output (str or None).
    """
    calls: list[dict[str, Any]] = []
    outputs_by_call_id: dict[str, str] = {}

    # First pass: collect all outputs keyed by call_id
    for item in trace.items:
        if item.type == "function_call_output":
            output = item.output
            if not isinstance(output, str):
                output = str(output)
            outputs_by_call_id[item.call_id] = output

    # Second pass: collect function calls
    for item in trace.items:
        if item.type == "function_call":
            args_str = item.arguments
            try:
                args = json.loads(args_str) if args_str else {}
            except (json.JSONDecodeError, TypeError):
                args = {}

            calls.append({
                "name": item.name,
                "arguments": args,
                "arguments_raw": args_str,
                "call_id": item.call_id,
                "created_by": getattr(item, "created_by", "unknown"),
                "output": outputs_by_call_id.get(item.call_id),
            })

    return calls


def _get_last_status_bar(trace: Any) -> str | None:
    """Find the last Status Bar text in any function_call_output."""
    for item in reversed(list(trace.items)):
        if item.type == "function_call_output":
            output = item.output if isinstance(item.output, str) else str(item.output)
            if "Status Bar" in output:
                for line in output.split("\n"):
                    if "Status Bar" in line:
                        return line.strip()
    return None


def _get_last_tool_output(
    trace_calls: list[dict[str, Any]],
    tool_name: str,
) -> str | None:
    """Return the output of the last call to *tool_name*, or None."""
    for call in reversed(trace_calls):
        if call["name"] == tool_name and call["output"] is not None:
            return call["output"]
    return None


# ---------------------------------------------------------------------------
# Action checks
# ---------------------------------------------------------------------------

def _check_actions(
    expected_actions: list[dict[str, Any]],
    trace_calls: list[dict[str, Any]],
) -> list[bool]:
    """Check whether each expected action was performed in the trace.

    Matching: function name + requestor/created_by.  Arguments are NOT
    compared (compare_args is always empty in this dataset).
    """
    results: list[bool] = []
    for action in expected_actions:
        name = action["name"]
        requestor = action["requestor"]
        found = any(
            tc["name"] == name and tc["created_by"] == requestor
            for tc in trace_calls
        )
        results.append(found)
    return results


# ---------------------------------------------------------------------------
# Environment assertion checks
# ---------------------------------------------------------------------------

def _check_env_assertions(
    env_assertions: list[dict[str, Any]],
    trace: Any,
    trace_calls: list[dict[str, Any]],
    init_actions: list[dict[str, Any]],
) -> list[bool]:
    """Evaluate each environment assertion from trace data."""
    results: list[bool] = []
    last_status_bar = _get_last_status_bar(trace)
    broken = {a["func_name"] for a in init_actions}
    trace_call_names = [tc["name"] for tc in trace_calls]

    for assertion in env_assertions:
        func = assertion["func_name"]
        args = assertion["arguments"]
        assert_value = assertion["assert_value"]

        met = _evaluate_single_assertion(
            func, args, assert_value,
            last_status_bar, trace_calls, trace_call_names, broken,
        )
        results.append(met)

    return results


def _evaluate_single_assertion(
    func: str,
    args: dict[str, Any],
    assert_value: bool,
    last_status_bar: str | None,
    trace_calls: list[dict[str, Any]],
    trace_call_names: list[str],
    broken: set[str],
) -> bool:
    """Dispatch to the correct assertion evaluator."""
    if func == "assert_service_status":
        return _assert_service_status(args, assert_value, last_status_bar, trace_calls)
    if func == "assert_can_send_mms":
        return _assert_can_send_mms(
            args, assert_value, last_status_bar, trace_calls, trace_call_names, broken,
        )
    if func == "assert_mobile_data_status":
        return _assert_mobile_data_status(args, assert_value, last_status_bar)
    if func == "assert_internet_speed":
        return _assert_internet_speed(args, assert_value, last_status_bar)
    if func == "assert_no_overdue_bill":
        return _assert_no_overdue_bill(args, assert_value, trace_calls, broken)
    if func == "assert_data_refueling_amount":
        return _assert_data_refueling_amount(args, assert_value, trace_calls)
    # Unknown assertion type — conservative: assume not met
    return False


# --- Individual assertion evaluators ---

def _assert_service_status(
    args: dict[str, Any],
    assert_value: bool,
    last_status_bar: str | None,
    trace_calls: list[dict[str, Any]],
) -> bool:
    expected = args["expected_status"]

    if last_status_bar is not None:
        has_signal = "\U0001f4f6" in last_status_bar  # 📶
        no_signal = "\U0001f4f5" in last_status_bar or "\u2708" in last_status_bar  # 📵 or ✈
        if expected == "connected":
            result = has_signal and not no_signal
        else:  # "no_service"
            result = no_signal or not has_signal
    else:
        # No status bar — check if agent transferred (service was never fixed)
        transferred = any(tc["name"] == "transfer_to_human_agents" for tc in trace_calls)
        if expected == "no_service":
            result = True  # service remains broken
        else:
            result = not transferred

    return result == assert_value


def _assert_can_send_mms(
    args: dict[str, Any],
    assert_value: bool,
    last_status_bar: str | None,
    trace_calls: list[dict[str, Any]],
    trace_call_names: list[str],
    broken: set[str],
) -> bool:
    expected = args["expected_status"]

    # Primary: use the last can_send_mms tool output (available ~99% of the time)
    last_mms_output = _get_last_tool_output(trace_calls, "can_send_mms")
    if last_mms_output is not None:
        can_mms = "can send MMS" in last_mms_output and "cannot" not in last_mms_output
        return (can_mms == expected) == assert_value

    # Fallback: infer from network state + APN + permissions
    if last_status_bar is None:
        # No status bar and no can_send_mms — conservative
        transferred = any(tc["name"] == "transfer_to_human_agents" for tc in trace_calls)
        inferred = not expected if transferred else False
        return (inferred == expected) == assert_value

    # Network conditions
    has_good_signal = "\U0001f4f6\u00b3" in last_status_bar or "\U0001f4f6\u2074" in last_status_bar
    has_data = "Data Enabled" in last_status_bar
    not_2g = "2G" not in last_status_bar
    network_ok = has_good_signal and has_data and not_2g

    # APN settings
    apn_broken = "break_apn_mms_setting" in broken
    apn_fixed = "reset_apn_settings" in trace_call_names
    apn_ok = (not apn_broken) or apn_fixed

    # App permissions
    sms_broken = "break_app_sms_permission" in broken or "break_app_both_permissions" in broken
    storage_broken = "break_app_storage_permission" in broken or "break_app_both_permissions" in broken

    sms_fixed = any(
        tc["name"] == "grant_app_permission" and tc["arguments"].get("permission") == "sms"
        for tc in trace_calls
    )
    storage_fixed = any(
        tc["name"] == "grant_app_permission" and tc["arguments"].get("permission") == "storage"
        for tc in trace_calls
    )
    sms_ok = (not sms_broken) or sms_fixed
    storage_ok = (not storage_broken) or storage_fixed

    can_mms = network_ok and apn_ok and sms_ok and storage_ok
    return (can_mms == expected) == assert_value


def _assert_mobile_data_status(
    args: dict[str, Any],
    assert_value: bool,
    last_status_bar: str | None,
) -> bool:
    expected = args["expected_status"]
    if last_status_bar is None:
        return False  # conservative
    has_data = "Data Enabled" in last_status_bar
    return (has_data == expected) == assert_value


def _assert_internet_speed(
    args: dict[str, Any],
    assert_value: bool,
    last_status_bar: str | None,
) -> bool:
    expected_desc = args["expected_desc"]
    if last_status_bar is None:
        return False  # conservative
    if expected_desc == "excellent":
        result = (
            "\U0001f4f6\u2074" in last_status_bar  # 📶⁴
            and "5G" in last_status_bar
            and "Data Enabled" in last_status_bar
        )
    elif expected_desc == "good":
        result = "\U0001f4f6\u00b3" in last_status_bar  # 📶³
    else:
        result = False
    return result == assert_value


def _assert_no_overdue_bill(
    args: dict[str, Any],
    assert_value: bool,
    trace_calls: list[dict[str, Any]],
    broken: set[str],
) -> bool:
    # If the bill was never made overdue in the initial state, it's not overdue.
    bill_was_overdue = "suspend_line_for_overdue_bill" in broken
    if not bill_was_overdue:
        no_overdue = True
    else:
        # Bill was overdue — check if the user made a payment
        no_overdue = any(tc["name"] == "make_payment" for tc in trace_calls)
    return (no_overdue == assert_value)


def _assert_data_refueling_amount(
    args: dict[str, Any],
    assert_value: bool,
    trace_calls: list[dict[str, Any]],
) -> bool:
    expected_amount = args["expected_amount"]
    customer_id = args["customer_id"]
    line_id = args["line_id"]

    refueled = any(
        tc["name"] == "refuel_data"
        and tc["arguments"].get("customer_id") == customer_id
        and tc["arguments"].get("line_id") == line_id
        and tc["arguments"].get("gb_amount") == expected_amount
        for tc in trace_calls
    )
    return (refueled == assert_value)


# ---------------------------------------------------------------------------
# Main scorer entry point
# ---------------------------------------------------------------------------

def compute_scores(sample: dict[str, Any], solver_output: Any) -> dict[str, Any]:
    """Score a tau2bench trace against its evaluation criteria.

    Parameters
    ----------
    sample : dict
        Dataset row with ``task_metadata``, ``reward_info``, etc.
    solver_output : SolverTrace
        Pass-through solver output.  ``solver_output.trace`` is a Pydantic
        ``Trace`` model with ``.items`` containing the conversation.
    """
    trace = solver_output.trace
    task_meta = sample["task_metadata"]
    eval_criteria = task_meta["evaluation_criteria"]
    init_actions = task_meta["initial_state"]["initialization_actions"]
    reward_basis = eval_criteria["reward_basis"]

    # Handle empty / failed traces (e.g. infrastructure_error in tau2bench)
    if not trace.items:
        gt_reward_info = sample.get("reward_info")
        gt_reward = _safe_get_reward(gt_reward_info)
        return {
            "reward": 0.0,
            "action_score": 0.0,
            "env_assertion_score": 0.0,
            "action_coverage": 0.0,
            "ground_truth_reward": gt_reward if gt_reward is not None else -1.0,
            "reward_match": gt_reward is None or abs(0.0 - gt_reward) < 0.01,
            "num_expected_actions": len(eval_criteria.get("actions") or []),
            "num_env_assertions": len(eval_criteria.get("env_assertions") or []),
            "reward_basis": ",".join(reward_basis),
            "empty_trace": True,
        }

    # Extract structured calls from trace
    trace_calls = _extract_function_calls(trace)

    # --- Action checks ---
    expected_actions = eval_criteria.get("actions") or []
    action_results = _check_actions(expected_actions, trace_calls)

    action_score = 1.0 if (not action_results or all(action_results)) else 0.0
    action_coverage = (
        sum(action_results) / len(action_results) if action_results else 1.0
    )

    # --- Environment assertion checks ---
    env_assertions = eval_criteria.get("env_assertions") or []
    env_results = _check_env_assertions(env_assertions, trace, trace_calls, init_actions)

    env_score = 1.0 if (not env_results or all(env_results)) else 0.0

    # --- Combine by reward_basis ---
    component_scores: dict[str, float] = {}
    if "ENV_ASSERTION" in reward_basis:
        component_scores["ENV_ASSERTION"] = env_score
    if "ACTION" in reward_basis:
        component_scores["ACTION"] = action_score

    reward = min(component_scores.values()) if component_scores else 1.0

    # --- Ground truth comparison ---
    gt_reward_info = sample.get("reward_info")
    gt_reward = _safe_get_reward(gt_reward_info)
    if gt_reward is not None:
        reward_match = abs(reward - gt_reward) < 0.01
    else:
        reward_match = True  # no ground truth to compare

    return {
        "reward": reward,
        "action_score": action_score,
        "env_assertion_score": env_score,
        "action_coverage": action_coverage,
        "ground_truth_reward": gt_reward if gt_reward is not None else -1.0,
        "reward_match": reward_match,
        "num_expected_actions": len(expected_actions),
        "num_env_assertions": len(env_assertions),
        "reward_basis": ",".join(reward_basis),
    }
