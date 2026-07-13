from typing import Any

from openai import OpenAI


def synthesize(source: dict[str, Any]) -> list[dict[str, Any]]:
    client = OpenAI(api_key="<< secrets.OPENAI_API_KEY >>")
    response = client.responses.create(
        model="gpt-5.5",
        instructions="You are a helpful data synthesis assistant.",
        input="""Please write several comma-separated Harry Potter questions in a single line?""",
    )
    return [{"question": question} for question in response.output_text.split(",")]
