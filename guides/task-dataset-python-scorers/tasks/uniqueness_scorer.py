from __future__ import annotations

from collections import Counter
from typing import Any


def compute_scores(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    field_name = "<< config.field >>"
    values = [
        sample[field_name] if field_name in sample else None for sample in samples
    ]
    counter = Counter(values)

    return [
        {"is_unique": counter[value] == 1 if value is not None else True}
        for value in values
    ]
