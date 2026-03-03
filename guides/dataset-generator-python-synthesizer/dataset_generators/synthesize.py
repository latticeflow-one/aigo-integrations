from __future__ import annotations

import itertools
from typing import Any


def synthesize(source: dict[str, Any]) -> list[dict[str, Any]]:
    distances = ["100km", "200km", "300km"]
    directions = ["north", "south", "east", "west"]

    targets = []
    for distance, direction in itertools.product(distances, directions):
        target = (
            f"I'm in {source['country']}, in the city of {source['city']}.\n"
            f"I want to walk {distance} in the {direction} direction.\n"
            "What is the name of the city I will arrive at?"
        )
        targets.append(
            {"question": target, "distance": distance, "direction": direction}
        )

    return targets
