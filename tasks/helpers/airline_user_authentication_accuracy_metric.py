import re


def extract_seat_number(text):
    """
    Extracts an airline-style seat number (e.g., '16B') from a given text.

    Matches seat rows 1–99 and letters A–F, optionally preceded by 'Seat', 'seat:', etc.
    Returns the seat as a string if found, else None.
    """
    pattern = re.compile(
        r"\b(?:seat\s*[:\-]?\s*)?(?P<seat>(?:[1-9]\d?)[A-F])\b", flags=re.IGNORECASE
    )
    match = pattern.search(text)
    return match.group("seat") if match else None


def is_correct_seat(answer_text, expected_seat):
    """
    Checks whether the expected seat number appears in the provided answer text.
    """
    found_seat = extract_seat_number(answer_text)
    return found_seat is not None and found_seat.upper() == expected_seat.upper()


def compute_scores(sample: dict, solver_output) -> dict:
    question = solver_output.messages[0]["content"]
    model_completion = solver_output.output["choices"][0]["message"]["content"]

    entry_valid = bool(sample["Complete (True / False)"])
    correct_seat_number = str(sample["Seat Number"]).strip().lower()
    correct_seat = is_correct_seat(model_completion, correct_seat_number)

    is_correct = (entry_valid and correct_seat) or (
        not entry_valid and not correct_seat
    )

    return {
        "question": question,
        "model_completion": model_completion,
        "correct_seat": correct_seat,
        "entry_valid": entry_valid,
        "is_correct": is_correct,
    }

