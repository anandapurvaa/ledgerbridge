# src/extraction/metrics.py
from __future__ import annotations

from typing import Any

import evaluate
import numpy as np

from src.extraction.sroie_preprocessor import ID_TO_LABEL

seqeval_metric = evaluate.load("seqeval")


def compute_token_classification_metrics(
    eval_prediction: Any,
) -> dict[str, float]:
    """
    Convert logits and labels into BIO sequences, excluding -100 labels,
    then compute entity-level seqeval metrics.
    """
    logits, labels = eval_prediction

    predictions = np.argmax(
        logits,
        axis=-1,
    )

    true_predictions: list[list[str]] = []
    true_labels: list[list[str]] = []

    for prediction_row, label_row in zip(
        predictions,
        labels,
        strict=True,
    ):
        prediction_sequence: list[str] = []
        label_sequence: list[str] = []

        for predicted_id, label_id in zip(
            prediction_row,
            label_row,
            strict=True,
        ):
            if int(label_id) == -100:
                continue

            prediction_sequence.append(
                ID_TO_LABEL[int(predicted_id)]
            )
            label_sequence.append(
                ID_TO_LABEL[int(label_id)]
            )

        true_predictions.append(prediction_sequence)
        true_labels.append(label_sequence)

    metrics = seqeval_metric.compute(
        predictions=true_predictions,
        references=true_labels,
        zero_division=0,
    )
    print(
    "seqeval metric keys:",
    list(metrics.keys()),
)

    result = {
        "precision": float(metrics["overall_precision"]),
        "recall": float(metrics["overall_recall"]),
        "f1": float(metrics["overall_f1"]),
        "accuracy": float(metrics["overall_accuracy"]),
    }

    for entity_name in ("VENDOR", "DATE", "TOTAL"):
        entity_metrics = (
            metrics.get(entity_name)
            or metrics.get(entity_name.lower())
            or {}
        )

        result[f"{entity_name.lower()}_precision"] = float(
            entity_metrics.get("precision", 0.0)
        )

        result[f"{entity_name.lower()}_recall"] = float(
            entity_metrics.get("recall", 0.0)
        )

        result[f"{entity_name.lower()}_f1"] = float(
            entity_metrics.get("f1", 0.0)
        )

    return result