from __future__ import annotations

import json
from typing import Any

import httpx


def run_inference(body: str, environment: dict[str, Any]) -> str:
    base_url = (
        environment["LANGSMITH_ENDPOINT_URL"].rstrip("/").removesuffix("/runs/wait")
    )
    api_key = environment["LANGSMITH_API_KEY"]
    assistant_id = environment["LANGSMITH_ASSISTANT_ID"]

    headers = {"X-Api-Key": api_key, "X-Auth-Scheme": "langsmith-api-key"}

    request_data = json.loads(body)
    request_messages = request_data.get("messages", [])

    # Get thread_id from the most recent message that has one
    thread_id = None
    for request_message in reversed(request_messages):
        if request_message.get("thread_id"):
            thread_id = request_message.get("thread_id")
            break

    # Create thread if needed
    if thread_id is None:
        response = httpx.post(
            f"{base_url}/threads", headers=headers, json={}, timeout=30
        )
        response.raise_for_status()
        thread_data = response.json()
        thread_id = thread_data["thread_id"]

    # Get the last user message
    user_text = ""
    for request_message in reversed(request_messages):
        if request_message.get("role") == "user":
            user_text = request_message.get("content", "")
            break

    # Send message to thread
    response = httpx.post(
        f"{base_url}/threads/{thread_id}/runs/wait",
        headers=headers,
        json={
            "assistant_id": assistant_id,
            "input": {"messages": [{"role": "user", "content": user_text}]},
        },
        timeout=120,
    )
    response.raise_for_status()
    response_data = response.json()

    # Extract final assistant response
    final_content = ""
    tool_calls = []

    for message in response_data.get("messages", []):
        # We expect only 1 such `ai` message
        if message.get("type") == "ai":
            content = message.get("content", "")
            if isinstance(content, str) and content:
                final_content = content
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text = part.get("text", "")
                        if text:
                            final_content = text

            message_tool_calls = message.get("tool_calls", [])
            if message_tool_calls:
                tool_calls.extend(message_tool_calls)

    # Build response message
    message = {"role": "assistant", "content": final_content, "thread_id": thread_id}

    if len(tool_calls) > 0:
        message["tool_calls"] = [
            {
                "id": tool_call.get("id"),
                "type": "function",
                "function": {
                    "name": tool_call.get("name"),
                    "arguments": json.dumps(tool_call.get("args", {})),
                },
            }
            for tool_call in tool_calls
        ]

    result = {
        "id": f"thread-{thread_id}",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    return json.dumps(result)
