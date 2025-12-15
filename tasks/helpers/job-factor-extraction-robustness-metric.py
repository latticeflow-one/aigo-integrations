from collections import defaultdict
from typing import Any
from typing import Callable
from typing import Literal

from latticeflow.assessment.brain.metrics.bleu import compute_bleu


ModelOutput = dict[Literal["factors"], list[dict[Literal["name", "description"], str]]]

import numpy as np
import spacy


nlp = spacy.load("/app/latticeflow-assessment/lf_data/data/files/spacy_en_core_web_sm")


def _compute_text_embedding(text: str) -> np.ndarray:
    document = nlp(text)
    vector: np.ndarray = document.vector
    return vector


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    numerator: float = float(np.dot(vec_a, vec_b))
    denominator: float = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def _semantic_similarity(text_a: str, text_b: str) -> float:
    embedding_a = _compute_text_embedding(text_a)
    embedding_b = _compute_text_embedding(text_b)
    return _cosine_similarity(embedding_a, embedding_b)


def _bleu_similarity(reference: str, prediction: str) -> float:
    return float(compute_bleu([[reference]], [prediction]))


def _equality(a: Any, b: Any) -> float:
    return float(a == b)


def _similarity(
    output_on_perturbed: ModelOutput,
    output_on_unchanged: ModelOutput,
    pairwise_similarity: Callable[[str, str], float],
) -> float:
    num_u = len(output_on_unchanged["factors"])
    num_p = len(output_on_perturbed["factors"])

    if num_u == 0 and num_p == 0:
        return 1.0
    elif num_u == 0 or num_p == 0:
        return 0.0

    # Compute the similarity matrix.
    matrix = [
        [
            pairwise_similarity(
                f"{factor_u['name']}: {factor_u['description']}",
                f"{factor_p['name']}: {factor_p['description']}",
            )
            for factor_p in output_on_perturbed["factors"]
        ]
        for factor_u in output_on_unchanged["factors"]
    ]

    # TODO: Here we should actually do some optimal matching of the factors.
    # For now, we just do a simple approximation:
    return min(
        # Average best match for each U
        sum(max(matrix[u][p] for p in range(num_p)) for u in range(num_u)) / num_u,
        # Average best match for each P
        sum(max(matrix[u][p] for u in range(num_u)) for p in range(num_p)) / num_p,
    )


def aggregate(scores: list[dict]) -> dict[str, float]:
    results = scores

    # Find the outputs on the unchanged inputs.
    job_id_to_output_on_unchanged: dict[str, ModelOutput] = {}
    for result in results:
        if result["variant"] != "unchanged":
            continue
        job_id_to_output_on_unchanged[result["job_id"]] = result["model_output"]

    # Compute the difference between the output on the perturbed input and the unchanged input.
    similarities: dict[str, list[float]] = defaultdict(list)
    for result in results:
        if result["variant"] == "unchanged":
            continue
        output_on_unchanged = job_id_to_output_on_unchanged[result["job_id"]]
        output_on_perturbed = result["model_output"]

        for similarity_name, pairwise_similarity_fn in (
            ("bleu", _bleu_similarity),
            ("semantic", _semantic_similarity),
            ("equality", _equality),
        ):
            similarities[f"{result['variant']}_{similarity_name}"].append(
                _similarity(
                    output_on_perturbed, output_on_unchanged, pairwise_similarity_fn
                )
            )

    return {
        variant: sum(values) / len(values) for variant, values in similarities.items()
    }
