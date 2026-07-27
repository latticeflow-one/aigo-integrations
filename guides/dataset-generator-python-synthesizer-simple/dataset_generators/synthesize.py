from __future__ import annotations

from typing import Any


def synthesize(source: dict[str, Any]) -> list[dict[str, Any]]:
    city = source["city"]
    celsius = float(source["temperature_celsius"])
    fahrenheit = celsius * 9 / 5 + 32

    return [
        {
            "question": f"It is {celsius:g} °C in {city}. What is that in Fahrenheit?",
            "answer": f"{fahrenheit:g} °F",
        },
        {
            "question": f"It is {fahrenheit:g} °F in {city}. What is that in Celsius?",
            "answer": f"{celsius:g} °C",
        },
    ]
