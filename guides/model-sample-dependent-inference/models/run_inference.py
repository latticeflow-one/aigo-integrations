from __future__ import annotations

import json
from typing import Any


def run_inference(body: str, environment: dict[str, Any], sample: dict[str, Any] | None = None) -> str:
    body_dict = json.loads(body)

    # Note: Normally we would call the model endpoint here.
    # response = httpx.post(
    #     ...
    # )

    # For demonstration purposes, we will return the sample text.
    response = sample["text"]

    return json.dumps({
        "choices": [
            {
            "message": {
                "role": "assistant",
                "content": response
            }
            }
        ]
    })
