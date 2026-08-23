# tests/extraction/test_metrics.py
import numpy as np

from src.extraction.metrics import (
    compute_token_classification_metrics,
)
from src.extraction.sroie_preprocessor import (
    LABEL_TO_ID,
)


def test_metrics_return_nonzero_entity_f1_for_correct_prediction():
    labels = np.array(
        [
            [
                -100,
                LABEL_TO_ID["B-VENDOR"],
                LABEL_TO_ID["I-VENDOR"],
                LABEL_TO_ID["O"],
                LABEL_TO_ID["B-DATE"],
                LABEL_TO_ID["B-TOTAL"],
                -100,
            ]
        ]
    )

    logits = np.zeros(
        (
            1,
            labels.shape[1],
            len(LABEL_TO_ID),
        ),
        dtype=np.float32,
    )

    for token_index, label_id in enumerate(labels[0]):
        if label_id != -100:
            logits[0, token_index, label_id] = 10.0

    metrics = compute_token_classification_metrics(
        (logits, labels),
    )

    assert metrics["f1"] == 1.0
    assert metrics["vendor_f1"] == 1.0
    assert metrics["date_f1"] == 1.0
    assert metrics["total_f1"] == 1.0