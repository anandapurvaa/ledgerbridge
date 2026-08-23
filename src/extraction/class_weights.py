# src/extraction/class_weights.py
from __future__ import annotations

from collections import Counter

import torch
from datasets import Dataset

from src.extraction.sroie_preprocessor import LABEL_LIST


def calculate_class_weights(
    dataset: Dataset,
    max_weight: float = 25.0,
) -> torch.Tensor:
    """
    Calculate smoothed inverse-frequency class weights from labels.

    - Ignores -100 labels: special tokens, padding, non-first subtokens.
    - Keeps O at 1.0.
    - Clips extreme rare-label weights for stable training on SROIE.
    """
    counts: Counter[int] = Counter()

    for labels in dataset["labels"]:
        for label_id in labels:
            label_value = int(label_id)

            if label_value != -100:
                counts[label_value] += 1

    if not counts:
        raise ValueError(
            "No valid labels found while calculating class weights."
        )

    o_label_id = 0
    o_count = counts[o_label_id]

    weights: list[float] = []

    for label_id in range(len(LABEL_LIST)):
        label_count = counts.get(label_id, 0)

        if label_count == 0:
            weight = max_weight
        else:
            weight = o_count / label_count

        weight = min(weight, max_weight)
        weights.append(float(weight))

    # Keep O explicitly at 1.0. Other classes get higher relative loss.
    weights[o_label_id] = 1.0

    return torch.tensor(
        weights,
        dtype=torch.float32,
    )


def format_class_weights(
    class_weights: torch.Tensor,
) -> dict[str, float]:
    return {
        label_name: round(
            float(class_weights[label_id]),
            4,
        )
        for label_id, label_name in enumerate(LABEL_LIST)
    }