# tests/extraction/test_class_weights.py
import torch
from datasets import Dataset

from src.extraction.class_weights import (
    calculate_class_weights,
)


def test_rare_entity_classes_receive_higher_weights():
    dataset = Dataset.from_dict(
        {
            "labels": [
                [0, 0, 0, 0, 1, 2, -100],
                [0, 0, 0, 3, 4, -100, -100],
                [0, 0, 5, 6, -100, -100, -100],
            ]
        }
    )

    weights = calculate_class_weights(
        dataset,
        max_weight=25.0,
    )

    assert isinstance(weights, torch.Tensor)
    assert weights[0].item() == 1.0

    assert weights[1].item() > weights[0].item()
    assert weights[3].item() > weights[0].item()
    assert weights[5].item() > weights[0].item()