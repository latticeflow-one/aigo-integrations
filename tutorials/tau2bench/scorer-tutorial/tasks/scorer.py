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


class TraceScorer:
    """Scores a single agent trace against per-sample evaluation criteria.

    All trace state (extracted calls, status bar, broken capabilities) is
    computed once in ``__init__`` and shared across assertion handlers via
    ``self``.
    """

    def __init__(self, trace: Any, init_actions: list[dict]) -> None:
        self.trace = trace
        self.calls = self.extract_calls()
        self.status_bar = self.find_last_status_bar()
        self.broken = {a["func_name"] for a in init_actions}

    # ── Trace helpers ───────────────────────────────────────────────

    def extract_calls(self) -> list[dict[str, Any]]:
        """Extract function calls paired with their outputs from the trace."""
        outputs: dict[str, str] = {}
        for item in self.trace.items:
            if item.type == "function_call_output":
                outputs[item.call_id] = (
                    item.output if isinstance(item.output, str) else str(item.output)
                )

        calls: list[dict[str, Any]] = []
        for item in self.trace.items:
            if item.type == "function_call":
                args = json.loads(item.arguments) if item.arguments else {}
                calls.append({
                    "name": item.name,
                    "args": args,
                    "created_by": item.created_by,
                    "output": outputs.get(item.call_id),
                })
        return calls

    def find_last_status_bar(self) -> str | None:
        """Return the last Status Bar line from any tool output."""
        for item in reversed(list(self.trace.items)):
            if item.type == "function_call_output":
                text = item.output if isinstance(item.output, str) else str(item.output)
                if "Status Bar" in text:
                    for line in text.split("\n"):
                        if "Status Bar" in line:
                            return line.strip()
        return None

    def last_tool_output(self, tool_name: str) -> str | None:
        """Return the output of the last call to *tool_name*."""
        for call in reversed(self.calls):
            if call["name"] == tool_name and call["output"] is not None:
                return call["output"]
        return None

    # ── Action checks ───────────────────────────────────────────────

    def check_actions(self, expected: list[dict]) -> list[bool]:
        """Check each expected action against the trace.

        Matches by (function name, requestor/created_by).
        Arguments are NOT compared — only presence matters.
        """
        return [
            any(
                c["name"] == action["name"] and c["created_by"] == action["requestor"]
                for c in self.calls
            )
            for action in expected
        ]

    # ── Environment assertions ──────────────────────────────────────

    def check_env_assertions(self, assertions: list[dict]) -> list[bool]:
        """Evaluate each environment assertion by dispatching to its handler.

        The assertion's ``func_name`` maps directly to a method on this class.
        """
        results = []
        for assertion in assertions:
            handler = getattr(self, assertion["func_name"], None)
            if handler is None:
                results.append(False)
                continue
            met = handler(assertion.get("arguments", {}))
            results.append(met == assertion.get("assert_value", True))
        return results

    def assert_service_status(self, expected: dict) -> bool:
        status = expected["expected_status"]
        if self.status_bar is not None:
            has_signal = "\U0001f4f6" in self.status_bar          # 📶
            no_signal = "\U0001f4f5" in self.status_bar or "\u2708" in self.status_bar  # 📵 ✈
            if status == "connected":
                return has_signal and not no_signal
            return no_signal or not has_signal
        transferred = any(c["name"] == "transfer_to_human_agents" for c in self.calls)
        return (not transferred) if status == "connected" else True

    def assert_mobile_data_status(self, expected: dict) -> bool:
        if self.status_bar is None:
            return False
        return ("Data Enabled" in self.status_bar) == expected["expected_status"]

    def assert_internet_speed(self, expected: dict) -> bool:
        if self.status_bar is None:
            return False
        desc = expected["expected_desc"]
        if desc == "excellent":
            return "\U0001f4f6\u2074" in self.status_bar and "5G" in self.status_bar and "Data Enabled" in self.status_bar
        if desc == "good":
            return "\U0001f4f6\u00b3" in self.status_bar
        return False

    def assert_can_send_mms(self, expected: dict) -> bool:
        output = self.last_tool_output("can_send_mms")
        if output is None:
            return False
        can_mms = "can send MMS" in output and "cannot" not in output
        return can_mms == expected["expected_status"]

    def assert_no_overdue_bill(self, expected: dict) -> bool:
        if "suspend_line_for_overdue_bill" not in self.broken:
            return True
        return any(c["name"] == "make_payment" for c in self.calls)

    def assert_data_refueling_amount(self, expected: dict) -> bool:
        return any(
            c["name"] == "refuel_data"
            and c["args"].get("customer_id") == expected["customer_id"]
            and c["args"].get("line_id") == expected["line_id"]
            and c["args"].get("gb_amount") == expected["expected_amount"]
            for c in self.calls
        )

    # ── Scoring ─────────────────────────────────────────────────────

    def score(self, criteria: dict) -> dict[str, Any]:
        """Score the trace against the given evaluation criteria."""
        action_results = self.check_actions(criteria.get("actions", []))
        action_score = 1.0 if all(action_results) else 0.0 if action_results else 1.0
        action_coverage = sum(action_results) / len(action_results) if action_results else 1.0

        env_results = self.check_env_assertions(criteria.get("env_assertions", []))
        env_score = 1.0 if all(env_results) else 0.0 if env_results else 1.0

        return {
            "score": min(action_score, env_score),
            "action_score": action_score,
            "env_assertion_score": env_score,
            "action_coverage": action_coverage,
        }


# ── Entry point ────────────────────────────────────────────────────────


def compute_scores(sample: dict[str, Any], solver_output: Any) -> dict[str, Any]:
    """Called once per sample by the AI GO! platform."""
    scorer = TraceScorer(solver_output.trace, sample["initial_state"]["initialization_actions"])
    return scorer.score(sample["evaluation_criteria"])
