from __future__ import annotations

import base64
import json
from typing import Any

import httpx


def get_user_message(messages) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")

    raise ValueError(f"Invalid input, no user message found in {messages}")


def get_session_id(messages: list) -> str | None:
    for message in messages:
        if message.get("session_id") is not None:
            return message.get("session_id")
    return None


def create_new_session(*, base_url: str, credentials: str | None = None) -> str:
    headers = {"Content-Type": "application/json"}
    if credentials is not None:
        headers["Authorization"] = f"Basic {credentials}"

    resp = httpx.post(f"{base_url}/session", content=b"{}", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]


def send_message(
    *,
    user_text: str,
    model_provider_id: str,
    model_id: str,
    session_id: str,
    base_url: str,
    credentials: str | None = None,
) -> str:
    message_payload = json.dumps(
        {
            "parts": [{"type": "text", "text": user_text}],
            "model": {"providerID": model_provider_id, "modelID": model_id},
        }
    ).encode()

    headers = {"Content-Type": "application/json"}
    if credentials is not None:
        headers["Authorization"] = f"Basic {credentials}"

    try:
        resp = httpx.post(
            f"{base_url}/session/{session_id}/message",
            content=message_payload,
            headers=headers,
            # Large number since this should be controlled via
            # the `timeout` field in the `model-opencode.yaml` file
            timeout=30 * 60,
        )
        resp.raise_for_status()
        response_json = resp.json()
    except Exception as e:
        raise Exception(
            f"Exception occurred when processing message {message_payload}: {e}"
        )

    full_response = ""
    for part in response_json.get("parts", []):
        if part.get("type") == "text":
            full_response += part.get("text", "")
    return full_response


def run_inference(body: str, environment: dict[str, Any]) -> str:
    base_url = environment["BASE_URL"].rstrip("/")
    model_provider_id = environment["MODEL_PROVIDER_ID"]
    model_id = environment["MODEL_ID"]

    username = environment.get("OPENCODE_USER", None)
    password = environment.get("OPENCODE_PASSWORD", None)

    if username and password:
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    else:
        credentials = None

    # Extract the last user message from the request body
    request_data = json.loads(body)
    messages = request_data.get("messages", [])
    user_text = get_user_message(messages)

    session_id = get_session_id(messages)
    if session_id is None:
        session_id = create_new_session(base_url=base_url, credentials=credentials)

    response_text = send_message(
        user_text=user_text,
        model_provider_id=model_provider_id,
        model_id=model_id,
        session_id=session_id,
        base_url=base_url,
        credentials=credentials,
    )

    # Return response in OpenAI chat completion format
    result = {
        "id": f"session-{session_id}",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text,
                    # include session_id such that we can retrieve it in the next iteration
                    "session_id": session_id,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    return json.dumps(result)
