from __future__ import annotations

import math
import random
from typing import Any


def synthesize(source: dict[str, Any]) -> list[dict[str, Any]]:
    rng = random.Random()

    def rand_int(lo: int = 0, hi: int = 20) -> int:
        return rng.randint(lo, hi)

    targets: list[dict[str, Any]] = []
    for operation in [
        "addition",
        "subtraction",
        "multiplication",
        "division",
        "factorial",
    ]:
        num_examples = rng.randint(1, 10)

        for _ in range(num_examples):
            if operation == "addition":
                a, b = rand_int(), rand_int()
                targets.append(
                    {
                        "operation": operation,
                        "expression": f"{a} + {b}",
                        "answer": a + b,
                    }
                )

            elif operation == "subtraction":
                a, b = rand_int(), rand_int()
                targets.append(
                    {
                        "operation": operation,
                        "expression": f"{a} - {b}",
                        "answer": a - b,
                    }
                )

            elif operation == "multiplication":
                a, b = rand_int(), rand_int()
                targets.append(
                    {
                        "operation": operation,
                        "expression": f"{a} * {b}",
                        "answer": a * b,
                    }
                )

            elif operation == "division":
                a = rand_int()
                b = rand_int(lo=1, hi=10)
                targets.append(
                    {
                        "operation": operation,
                        "expression": f"{a} / {b}",
                        "answer": a / b,
                    }
                )

            elif operation == "factorial":
                n = rand_int(lo=0, hi=20)
                targets.append(
                    {
                        "operation": operation,
                        "expression": f"{n}!",
                        "answer": math.factorial(n),
                    }
                )

    return targets
