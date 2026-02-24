import json

import httpx


def run_inference(body: str, environment: dict):
    body_dict = json.loads(body)
    body_dict["model"] = environment["MODEL_KEY"]

    response = httpx.post(
        environment["MODEL_ENDPOINT_URL"],
        headers={
            "Authorization": f"Bearer {environment['MODEL_ENDPOINT_API_KEY']}",
            "Content-Type": "application/json",
        },
        content=json.dumps(body_dict).encode(),
        timeout=10.0,
        verify=True,
    )
    response.raise_for_status()
    return response.text
