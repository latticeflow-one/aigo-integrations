"""LatticeFlow custom inference for a LangGraph Platform deployment.

Calls `POST /threads/{thread_id}/runs/wait` on a LangSmith-managed LangGraph
deployment and returns the full agent trace (tool calls + final reply) in
the Open Responses shape.
"""

# Example body (LatticeFlow → run_inference)
# {
#   "messages": [
#     {"role": "user", "content": "Search the catalog for shoes."}
#   ]
# }
#
# Multi-turn (subsequent turns echo the prior assistant message with
# `thread_id` so we keep using the same LangGraph thread):
# {
#   "messages": [
#     {"role": "user", "content": "Hello!"},
#     {"role": "assistant", "content": "Hello! How can I assist you today?",
#      "thread_id": "019e3d95-1898-7961-b0ed-536ac8c43757"},
#     {"role": "user", "content": "What is my thread id?"}
#   ]
# }

# Example raw model output (agent API → query_model)
# `/runs/wait` returns the final thread state. query_model wraps it with the
# thread_id we used so convert_model_output can echo it back.
# {
#   "thread_id": "019e3d95-45a7-7051-9e3a-c42ca0fbe182",
#   "final_state": {
#     "messages": [
#       {"type": "human", "content": "Search the catalog for shoes.",
#        "id": "adfea54d-..."},
#       {"type": "ai", "content": "", "id": "lc_run--...",
#        "tool_calls": [{"name": "search_products",
#                         "args": {"query": "shoes"},
#                         "id": "call_DwNd...", "type": "tool_call"}],
#        "usage_metadata": {"input_tokens": 177, "output_tokens": 15}},
#       {"type": "tool", "content": "[]", "name": "search_products",
#        "tool_call_id": "call_DwNd...", "status": "success"},
#       {"type": "ai",
#        "content": "I couldn't find any shoes in the catalog. ...",
#        "id": "lc_run--...",
#        "usage_metadata": {"input_tokens": 201, "output_tokens": 22}}
#     ]
#   }
# }

# Example LF model output (convert_model_output)
# {
#   "items": [
#     {"type": "function_call", "id": "5bf9...", "call_id": "call_DwNd...",
#      "name": "search_products", "arguments": "{\"query\": \"shoes\"}",
#      "status": "completed"},
#     {"type": "function_call_output", "id": "9da4...",
#      "call_id": "call_DwNd...", "output": "[]", "status": "completed"},
#     {"type": "message", "id": "44c2...", "status": "completed",
#      "role": "assistant",
#      "content": [{"type": "output_text",
#                   "text": "I couldn't find any shoes in the catalog. ...",
#                   "annotations": []}],
#      "thread_id": "019e3d95-45a7-7051-9e3a-c42ca0fbe182"}
#   ],
#   "usage": {"num_prompt_tokens": 378, "num_completion_tokens": 37}
# }

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx


# Example body (LatticeFlow → run_inference) — see file top
def convert_user_input(data: dict) -> dict:
    """Pull the latest user turn + reuse a thread_id echoed by a prior assistant."""
    messages = data["messages"]
    last_user = next(m for m in reversed(messages) if m.get("role") == "user")

    thread_id = ""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            thread_id = msg.get("thread_id", "") or ""
            break

    return {"thread_id": thread_id, "user_message": last_user["content"]}


# Example raw model output (agent API → query_model) — see file top
def query_model(model_input: dict, environment: dict) -> dict:
    """Create a thread if needed, then POST /runs/wait and return final state."""
    base_url = environment["LANGSMITH_DEPLOY_URL"].rstrip("/")
    api_key = environment["LANGSMITH_API_KEY"]
    assistant_id = environment["LANGGRAPH_ASSISTANT_ID"]

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=120) as client:
        thread_id = model_input["thread_id"]
        if not thread_id:
            create = client.post(f"{base_url}/threads", headers=headers, json={})
            create.raise_for_status()
            thread_id = create.json()["thread_id"]

        run = client.post(
            f"{base_url}/threads/{thread_id}/runs/wait",
            headers=headers,
            json={
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {"role": "user", "content": model_input["user_message"]}
                    ]
                },
            },
        )
        run.raise_for_status()
        final_state = run.json()

    return {"thread_id": thread_id, "final_state": final_state}


# Example LF model output (convert_model_output) — see file top
def convert_model_output(raw: dict) -> dict:
    thread_id = raw["thread_id"]
    messages = raw["final_state"].get("messages", [])

    # `/runs/wait` returns the FULL thread state. Keep only messages produced
    # by this turn — everything after the last human message.
    last_human = -1
    for i, msg in enumerate(messages):
        if msg.get("type") == "human":
            last_human = i
    turn_messages = messages[last_human + 1 :] if last_human >= 0 else messages

    items: list[dict[str, Any]] = []
    num_prompt_tokens = 0
    num_completion_tokens = 0
    final_text = ""

    for msg in turn_messages:
        msg_type = msg.get("type")
        if msg_type == "ai":
            usage = msg.get("usage_metadata") or {}
            num_prompt_tokens += usage.get("input_tokens", 0) or 0
            num_completion_tokens += usage.get("output_tokens", 0) or 0

            for call in msg.get("tool_calls") or []:
                items.append(
                    {
                        "type": "function_call",
                        "id": str(uuid.uuid4()),
                        "call_id": call["id"],
                        "name": call["name"],
                        "arguments": json.dumps(call.get("args") or {}),
                        "status": "completed",
                    }
                )

            content = msg.get("content") or ""
            if isinstance(content, str) and content.strip():
                final_text = content
        elif msg_type == "tool":
            items.append(
                {
                    "type": "function_call_output",
                    "id": str(uuid.uuid4()),
                    "call_id": msg["tool_call_id"],
                    "output": msg.get("content") or "",
                    "status": "completed",
                }
            )

    items.append(
        {
            "type": "message",
            "id": str(uuid.uuid4()),
            "status": "completed",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": final_text,
                    "annotations": [],
                }
            ],
            "thread_id": thread_id,
        }
    )

    return {
        "items": items,
        "usage": {
            "num_prompt_tokens": num_prompt_tokens,
            "num_completion_tokens": num_completion_tokens,
        },
    }


def run_inference(body: str, environment: dict) -> str:
    data = json.loads(body)
    model_input = convert_user_input(data)
    raw = query_model(model_input, environment)
    return json.dumps(convert_model_output(raw))


def test_run_inference() -> None:
    try:
        from pathlib import Path

        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent / ".env")
    except ImportError:
        pass

    import os

    environment = {
        "LANGSMITH_DEPLOY_URL": os.environ["LANGSMITH_DEPLOY_URL"],
        "LANGSMITH_API_KEY": os.environ["LANGSMITH_API_KEY"],
        "LANGGRAPH_ASSISTANT_ID": os.environ["LANGGRAPH_ASSISTANT_ID"],
    }

    def last_assistant_message(payload: dict) -> dict:
        return next(i for i in reversed(payload["items"]) if i["type"] == "message")

    print("=== Turn 1: greeting ===")
    turn1_in = {
        "messages": [
            {"role": "user", "content": "Hi, can you help me see my orders?"},
        ]
    }
    turn1_out = run_inference(json.dumps(turn1_in), environment)
    turn1_payload = json.loads(turn1_out)
    print(json.dumps(turn1_payload, indent=2))

    turn1_assistant = last_assistant_message(turn1_payload)

    print("\n=== Turn 2: email (should trigger authenticate tool) ===")
    turn2_in = {
        "messages": [
            {"role": "user", "content": "Hi, can you help me see my orders?"},
            {
                "role": "assistant",
                "content": turn1_assistant["content"][0]["text"],
                "thread_id": turn1_assistant["thread_id"],
            },
            {"role": "user", "content": "My email is alice@example.com"},
        ]
    }
    turn2_out = run_inference(json.dumps(turn2_in), environment)
    turn2_payload = json.loads(turn2_out)
    print(json.dumps(turn2_payload, indent=2))

    turn2_assistant = last_assistant_message(turn2_payload)

    print("\n=== Turn 3: order id (should trigger list_orders tool) ===")
    turn3_in = {
        "messages": [
            {"role": "user", "content": "Hi, can you help me see my orders?"},
            {
                "role": "assistant",
                "content": turn1_assistant["content"][0]["text"],
                "thread_id": turn1_assistant["thread_id"],
            },
            {"role": "user", "content": "My email is alice@example.com"},
            {
                "role": "assistant",
                "content": turn2_assistant["content"][0]["text"],
                "thread_id": turn2_assistant["thread_id"],
            },
            {"role": "user", "content": "My order ID is ORD-1001"},
        ]
    }
    turn3_out = run_inference(json.dumps(turn3_in), environment)
    print(json.dumps(json.loads(turn3_out), indent=2))


if __name__ == "__main__":
    test_run_inference()
