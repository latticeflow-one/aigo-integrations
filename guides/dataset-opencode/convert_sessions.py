#!/usr/bin/env python3
"""Convert OpenCode exported session JSONs into AI GO! Trace JSONL dataset.

Usage:
    python convert_sessions.py [--num-samples N] [--session-dir DIR] [--output FILE]

Reads all session JSON files from --session-dir, identifies root sessions
(those without a parentID), randomly selects --num-samples of them, converts
each to a latticeflow.assessment.dtypes.Trace, and writes the result as JSONL
with columns: trace (serialized Trace dict), source ("opencode").

Child/sub-agent sessions are automatically loaded and embedded as spans.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from latticeflow.assessment.dtypes import (
    CompactionEvent,
    CustomEvent,
    ErrorEvent,
    FunctionCallEvent,
    MessageEvent,
    ModelCallEvent,
    ModelUsage,
    SpanBeginEvent,
    SpanEndEvent,
    Trace,
    TraceMetadata,
)
from latticeflow.assessment.dtypes import (
    SYNTHETIC_MESSAGE_STATUS as STATUS,
)
from latticeflow.bindings.open_responses.models import (
    FunctionCallStatus,
    MessageRole,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MESSAGE_ID_COUNTER = 0


def _msg_id() -> str:
    global _MESSAGE_ID_COUNTER
    _MESSAGE_ID_COUNTER += 1
    return f"msg_{_MESSAGE_ID_COUNTER:06d}"


def _make_user_message(
    texts: list[str],
) -> dict[str, Any]:
    """Build a raw Open Responses user message dict."""
    return {
        "type": "message",
        "id": _msg_id(),
        "status": STATUS.value,
        "role": MessageRole.user.value,
        "content": [{"type": "input_text", "text": t} for t in texts],
    }


def _make_assistant_message(
    content_parts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a raw Open Responses assistant message dict.

    content_parts should be dicts like {"type": "output_text", "text": ...}
    or {"type": "reasoning_text", "text": ...}.
    """
    return {
        "type": "message",
        "id": _msg_id(),
        "status": STATUS.value,
        "role": MessageRole.assistant.value,
        "content": content_parts,
    }


def _ts(epoch_ms: int | float | None) -> datetime | None:
    """Convert epoch milliseconds to a UTC datetime, or None."""
    if epoch_ms is None:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)


def _safe_json(value: Any) -> str:
    """Serialize value to JSON string; return raw string if already a string."""
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


# ---------------------------------------------------------------------------
# Session index
# ---------------------------------------------------------------------------


def build_session_index(session_dir: Path) -> dict[str, dict[str, Any]]:
    """Build an index mapping session_id -> {path, info, is_root}.

    Only reads the info block (first ~20 lines) for speed.
    """
    index: dict[str, dict[str, Any]] = {}
    for path in sorted(session_dir.glob("ses_*.json")):
        try:
            data = json.loads(path.read_text())
            info = data["info"]
            session_id = info["id"]
            parent_id = info.get("parentID")
            index[session_id] = {
                "path": path,
                "info": info,
                "is_root": parent_id is None,
            }
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Skip %s: %s", path.name, exc)
    return index


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------


class SessionConverter:
    """Converts an OpenCode session JSON into a list of TraceEvents."""

    def __init__(self, session_index: dict[str, dict[str, Any]]) -> None:
        self._index = session_index
        # Track total tokens/cost across all steps for metadata.
        self._total_tokens = 0
        self._total_cost = 0.0
        self._model_id: str | None = None

    def convert(self, session_id: str) -> Trace:
        """Convert a root session to a Trace."""
        self._total_tokens = 0
        self._total_cost = 0.0
        self._model_id = None

        entry = self._index[session_id]
        data = json.loads(entry["path"].read_text())
        info = data["info"]
        messages = data.get("messages", [])

        events = self._convert_messages(messages, span_id=None)

        metadata = TraceMetadata(
            trace_id=session_id,
            source_type="opencode",
            agent="opencode",
            model=self._model_id,
            created_at=_ts(info["time"]["created"]),
            total_time=self._compute_total_time(info),
            total_tokens=self._total_tokens if self._total_tokens > 0 else None,
            message_count=len(messages),
            extra={
                "title": info.get("title", ""),
                "directory": info.get("directory", ""),
                "version": info.get("version", ""),
                "cost": self._total_cost,
                "slug": info.get("slug", ""),
            },
        )

        # Ensure timestamp consistency: sort_events_by_span requires either
        # all events have timestamps or none do. Backfill any missing ones
        # with the session creation time.
        fallback_ts = _ts(info["time"]["created"])
        for event in events:
            if event.timestamp is None:
                event.timestamp = fallback_ts

        trace = Trace.from_events(events, metadata=metadata)
        return trace

    def _compute_total_time(self, info: dict[str, Any]) -> float | None:
        time_data = info.get("time", {})
        created = time_data.get("created")
        updated = time_data.get("updated")
        if created is not None and updated is not None:
            return (updated - created) / 1000.0
        return None

    def _convert_messages(
        self,
        messages: list[dict[str, Any]],
        span_id: str | None,
    ) -> list[
        MessageEvent
        | FunctionCallEvent
        | ModelCallEvent
        | SpanBeginEvent
        | SpanEndEvent
        | CompactionEvent
        | ErrorEvent
        | CustomEvent
    ]:
        """Convert a list of OpenCode messages into TraceEvents.

        Groups consecutive assistant messages (same parentID) into a single
        logical assistant turn, emitting one MessageEvent for text content
        and individual FunctionCallEvents/ModelCallEvents per step.
        """
        events: list[Any] = []

        # Group messages: user messages standalone, consecutive assistant
        # messages with same parentID grouped together.
        grouped = self._group_messages(messages)

        for group in grouped:
            role = group[0]["info"]["role"]
            if role == "user":
                events.extend(self._convert_user_message(group[0], span_id))
            elif role == "assistant":
                events.extend(self._convert_assistant_turn(group, span_id))

        return events

    def _group_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        """Group messages: user messages are standalone, consecutive assistant
        messages sharing the same parentID are grouped together."""
        groups: list[list[dict[str, Any]]] = []
        current_group: list[dict[str, Any]] = []
        current_parent_id: str | None = None

        for msg in messages:
            role = msg["info"]["role"]
            if role == "user":
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    current_parent_id = None
                groups.append([msg])
            elif role == "assistant":
                parent_id = msg["info"].get("parentID")
                if current_group and parent_id == current_parent_id:
                    current_group.append(msg)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [msg]
                    current_parent_id = parent_id

        if current_group:
            groups.append(current_group)

        return groups

    def _convert_user_message(
        self,
        msg: dict[str, Any],
        span_id: str | None,
    ) -> list[Any]:
        """Convert a user message into events."""
        events: list[Any] = []
        parts = msg.get("parts", [])
        timestamp = _ts(msg["info"]["time"]["created"])

        # Collect text parts.
        texts: list[str] = []
        for part in parts:
            part_type = part.get("type")
            if part_type == "text":
                text = part.get("text", "")
                if text:
                    texts.append(text)
            elif part_type == "compaction":
                events.append(
                    CompactionEvent(
                        span_id=span_id,
                        timestamp=timestamp,
                        strategy="summary",
                    )
                )
            elif part_type == "file":
                # File attachment -- include filename in text.
                filename = part.get("filename", "attachment")
                texts.append(f"[Attached file: {filename}]")

        if texts:
            user_msg = _make_user_message(texts)
            events.append(
                MessageEvent(
                    span_id=span_id,
                    timestamp=timestamp,
                    item=user_msg,
                )
            )

        return events

    def _convert_assistant_turn(
        self,
        assistant_messages: list[dict[str, Any]],
        span_id: str | None,
    ) -> list[Any]:
        """Convert a group of assistant messages (one logical turn) into events.

        Produces:
        - One ModelCallEvent per step (step-start to step-finish)
        - FunctionCallEvents for each tool call
        - One consolidated MessageEvent for all text/reasoning output
        - SpanBegin/SpanEnd for sub-agent task tool calls
        - ErrorEvent for errors
        """
        events: list[Any] = []

        # Collect all text/reasoning content across steps for the consolidated
        # assistant MessageEvent.
        all_content_parts: list[dict[str, Any]] = []

        # Track items produced per step for ModelCallEvent.output_items.
        # We accumulate input context as we go (messages seen so far).
        accumulated_items: list[dict[str, Any]] = []

        for msg in assistant_messages:
            msg_info = msg["info"]
            parts = msg.get("parts", [])

            # Extract model info.
            model_id = msg_info.get("modelID", "")
            provider_id = msg_info.get("providerID", "")
            if model_id and self._model_id is None:
                self._model_id = (
                    f"{provider_id}/{model_id}" if provider_id else model_id
                )

            # Track cost.
            self._total_cost += msg_info.get("cost", 0.0)

            # Check for error on this message.
            error_info = msg_info.get("error")
            if error_info:
                error_name = error_info.get("name", "UnknownError")
                error_data = error_info.get("data", {})
                error_message = error_data.get("message", error_name)
                # Don't emit ErrorEvent for simple aborts -- those are just
                # the user cancelling, not real errors.
                if error_name != "MessageAbortedError":
                    events.append(
                        ErrorEvent(
                            span_id=span_id,
                            timestamp=_ts(msg_info.get("time", {}).get("created")),
                            message=f"{error_name}: {error_message}",
                        )
                    )

            # Process parts within this message, respecting step boundaries.
            step_parts: list[dict[str, Any]] = []
            step_start_time: int | None = None
            step_token_info: dict[str, Any] | None = None
            step_model_id = model_id

            for part in parts:
                part_type = part.get("type")

                if part_type == "step-start":
                    step_parts = []
                    step_start_time = None
                    step_token_info = None

                elif part_type == "step-finish":
                    step_token_info = part.get("tokens", {})
                    step_cost = part.get("cost", 0.0)

                    # Build ModelCallEvent for this step.
                    step_output_items = self._extract_step_output_items(step_parts)
                    input_tokens = step_token_info.get("input", 0)
                    output_tokens = step_token_info.get("output", 0)
                    reasoning_tokens = step_token_info.get("reasoning", 0)
                    cache_read = step_token_info.get("cache", {}).get("read", 0)
                    cache_write = step_token_info.get("cache", {}).get("write", 0)

                    total_step_tokens = input_tokens + output_tokens + reasoning_tokens
                    self._total_tokens += total_step_tokens

                    mc_event = ModelCallEvent(
                        span_id=span_id,
                        timestamp=_ts(step_start_time),
                        model=f"{provider_id}/{step_model_id}"
                        if provider_id
                        else step_model_id,
                        input_context=list(accumulated_items),
                        output_items=step_output_items,
                        usage=ModelUsage(
                            num_prompt_tokens=input_tokens + cache_read,
                            num_completion_tokens=output_tokens + reasoning_tokens,
                        ),
                        total_time=self._compute_step_time(step_parts),
                        metadata={
                            "cost": step_cost,
                            "cache_read_tokens": cache_read,
                            "cache_write_tokens": cache_write,
                        },
                    )
                    events.append(mc_event)

                    # Update accumulated items with this step's outputs.
                    accumulated_items.extend(step_output_items)

                elif part_type == "text":
                    text = part.get("text", "")
                    if text:
                        step_parts.append(part)
                        all_content_parts.append(
                            {
                                "type": "output_text",
                                "text": text,
                                "annotations": [],
                            }
                        )
                    if step_start_time is None:
                        time_data = part.get("time", {})
                        step_start_time = time_data.get("start")

                elif part_type == "reasoning":
                    text = part.get("text", "")
                    if text:
                        step_parts.append(part)
                        all_content_parts.append(
                            {"type": "reasoning_text", "text": text}
                        )
                    if step_start_time is None:
                        time_data = part.get("time", {})
                        step_start_time = time_data.get("start")

                elif part_type == "tool":
                    step_parts.append(part)
                    tool_events = self._convert_tool_part(
                        part, span_id, mc_event_id=None
                    )
                    events.extend(tool_events)

                    if step_start_time is None:
                        time_data = part.get("state", {}).get("time", {})
                        step_start_time = time_data.get("start")

        # Emit consolidated assistant MessageEvent with all text/reasoning.
        if all_content_parts:
            # Use the timestamp of the first assistant message.
            first_ts = _ts(assistant_messages[0]["info"].get("time", {}).get("created"))
            events.append(
                MessageEvent(
                    span_id=span_id,
                    timestamp=first_ts,
                    item=_make_assistant_message(all_content_parts),
                )
            )

        return events

    def _extract_step_output_items(
        self, step_parts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract Open Responses items produced by a single step.

        Used for ModelCallEvent.output_items.
        """
        items: list[dict[str, Any]] = []
        text_parts: list[dict[str, Any]] = []
        reasoning_parts: list[dict[str, Any]] = []

        for part in step_parts:
            part_type = part.get("type")
            if part_type == "text":
                text = part.get("text", "")
                if text:
                    text_parts.append(
                        {"type": "output_text", "text": text, "annotations": []}
                    )
            elif part_type == "reasoning":
                text = part.get("text", "")
                if text:
                    reasoning_parts.append({"type": "reasoning_text", "text": text})
            elif part_type == "tool":
                call_id = part.get("callID", str(uuid.uuid4()))
                tool_name = part.get("tool", "unknown")
                state = part.get("state", {})
                arguments = _safe_json(state.get("input", {}))
                items.append(
                    {
                        "type": "function_call",
                        "id": str(uuid.uuid4()),
                        "call_id": call_id,
                        "name": tool_name,
                        "arguments": arguments,
                        "status": FunctionCallStatus.completed.value,
                    }
                )

        # If there were text/reasoning parts, add as an assistant message.
        content = reasoning_parts + text_parts
        if content:
            items.insert(
                0,
                _make_assistant_message(content),
            )

        return items

    def _compute_step_time(self, step_parts: list[dict[str, Any]]) -> float | None:
        """Compute wall-clock time for a step from part timestamps."""
        start_times: list[float] = []
        end_times: list[float] = []
        for part in step_parts:
            time_data = part.get("time") or part.get("state", {}).get("time")
            if time_data:
                if "start" in time_data:
                    start_times.append(time_data["start"])
                if "end" in time_data:
                    end_times.append(time_data["end"])
        if start_times and end_times:
            return (max(end_times) - min(start_times)) / 1000.0
        return None

    def _convert_tool_part(
        self,
        part: dict[str, Any],
        span_id: str | None,
        mc_event_id: str | None,
    ) -> list[Any]:
        """Convert a tool part into FunctionCallEvent(s) and optionally spans."""
        events: list[Any] = []
        tool_name = part.get("tool", "unknown")
        call_id = part.get("callID", str(uuid.uuid4()))
        state = part.get("state", {})

        status_str = state.get("status", "completed")
        if status_str == "error":
            fc_status = FunctionCallStatus.incomplete
        elif status_str == "running":
            fc_status = FunctionCallStatus.in_progress
        else:
            fc_status = FunctionCallStatus.completed

        arguments = _safe_json(state.get("input", {}))
        output = state.get("output", "")
        if not isinstance(output, str):
            output = _safe_json(output)

        error_msg = state.get("error")

        # Compute working time from tool state timestamps.
        time_data = state.get("time", {})
        working_time: float | None = None
        start_ms = time_data.get("start")
        end_ms = time_data.get("end")
        if start_ms is not None and end_ms is not None:
            working_time = (end_ms - start_ms) / 1000.0

        timestamp = _ts(start_ms)

        # Handle sub-agent task tool calls -> spans.
        if tool_name == "task":
            child_session_id = state.get("metadata", {}).get("sessionId")
            task_description = state.get("input", {}).get(
                "description", "sub-agent task"
            )
            subagent_type = state.get("input", {}).get("subagent_type", "unknown")
            span_name = f"{subagent_type}: {task_description}"

            if child_session_id and child_session_id in self._index:
                # Emit span with full child session events.
                child_span_id = child_session_id

                events.append(
                    SpanBeginEvent(
                        span_id=child_span_id,
                        parent_span_id=span_id,
                        name=span_name,
                        span_type="agent",
                        timestamp=timestamp,
                    )
                )

                # Recursively convert child session.
                child_data = json.loads(
                    self._index[child_session_id]["path"].read_text()
                )
                child_messages = child_data.get("messages", [])
                child_events = self._convert_messages(
                    child_messages, span_id=child_span_id
                )
                events.extend(child_events)

                events.append(
                    SpanEndEvent(
                        span_id=child_span_id,
                        timestamp=_ts(end_ms),
                    )
                )

                # Root-level FunctionCallEvent linking to the span.
                events.append(
                    FunctionCallEvent(
                        span_id=span_id,
                        timestamp=timestamp,
                        call_id=call_id,
                        function=tool_name,
                        arguments=arguments,
                        result=output[:2000] if len(output) > 2000 else output,
                        status=fc_status,
                        working_time=working_time,
                        error=error_msg,
                        agent=subagent_type,
                        agent_span_id=child_span_id,
                        model_call_id=mc_event_id,
                    )
                )
                return events

        # Standard tool call -> FunctionCallEvent.
        # Truncate very long outputs to keep dataset manageable.
        max_output_len = 10000
        if len(output) > max_output_len:
            output = (
                output[:max_output_len]
                + f"\n... [truncated, {len(output)} chars total]"
            )

        events.append(
            FunctionCallEvent(
                span_id=span_id,
                timestamp=timestamp,
                call_id=call_id,
                function=tool_name,
                arguments=arguments,
                result=output,
                status=fc_status,
                working_time=working_time,
                error=error_msg,
                model_call_id=mc_event_id,
            )
        )

        return events


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert OpenCode sessions to AI GO! Trace JSONL."
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=10,
        help="Number of root sessions to convert (0 = all). Default: 10.",
    )
    parser.add_argument(
        "--session-dir",
        type=Path,
        default=Path(__file__).parent / "session_data",
        help="Directory containing ses_*.json files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "opencode_traces.jsonl",
        help="Output JSONL file path.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for session selection.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Build index.
    logger.info("Scanning sessions in %s ...", args.session_dir)
    index = build_session_index(args.session_dir)
    logger.info("Found %d total sessions.", len(index))

    # Filter root sessions.
    root_ids = [sid for sid, entry in index.items() if entry["is_root"]]
    logger.info("Found %d root sessions.", len(root_ids))

    # Select samples.
    if args.num_samples > 0 and args.num_samples < len(root_ids):
        rng = random.Random(args.seed)
        selected = rng.sample(root_ids, args.num_samples)
    else:
        selected = root_ids

    logger.info("Converting %d sessions ...", len(selected))

    converter = SessionConverter(index)
    rows_written = 0

    with open(args.output, "w") as out_file:
        for session_id in selected:
            try:
                trace = converter.convert(session_id)
                # Validate round-trip.
                trace_dict = trace.model_dump(mode="json")
                Trace.model_validate(trace_dict)

                row = {"trace": trace_dict, "source": "opencode"}
                out_file.write(json.dumps(row, default=str) + "\n")
                rows_written += 1

                title = index[session_id]["info"].get("title", "")
                n_items = len(trace.items)
                n_events = len(trace.events) if trace.events else 0
                n_spans = len(trace.spans())
                logger.info(
                    "  [%d] %s: %d items, %d events, %d spans — %s",
                    rows_written,
                    session_id,
                    n_items,
                    n_events,
                    n_spans,
                    title[:60],
                )
            except Exception:
                logger.exception("Failed to convert %s", session_id)

    logger.info("Wrote %d rows to %s", rows_written, args.output)


if __name__ == "__main__":
    main()
