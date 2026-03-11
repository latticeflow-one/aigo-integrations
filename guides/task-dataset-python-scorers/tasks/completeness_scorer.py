from __future__ import annotations

from typing import Any


def compute_scores(sample: dict[str, Any]) -> dict[str, Any]:
    field_name = "<< config.field >>"

    field_value = sample.get(field_name, None)
    has_field = field_name in sample and not isinstance(field_value, float)

    empty_field = isinstance(field_value, float) or (
        isinstance(field_value, str) and len(field_value) == 0
    )

    is_complete = has_field and not empty_field
    return {
        "is_complete": is_complete,
        "has_field": has_field,
        "empty_field": empty_field,
    }
