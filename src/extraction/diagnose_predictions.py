# src/extraction/diagnose_predictions.py
from __future__ import annotations

from collections import Counter

import torch

from src.extraction.layoutlmv3_dataset import (
    create_encoded_sroie,
)
from src.extraction.layoutlmv3_inference import (
    LayoutLMv3Extractor,
)
from src.extraction.sroie_preprocessor import ID_TO_LABEL


def main() -> None:
    dataset = create_encoded_sroie()

    extractor = LayoutLMv3Extractor(
        model_dir="models/layoutlmv3_lora_weighted_smoke",
    )

    example = dataset["test"][0]

    inputs = {
        "input_ids": example["input_ids"]
        .unsqueeze(0)
        .to(extractor.device),
        "attention_mask": example["attention_mask"]
        .unsqueeze(0)
        .to(extractor.device),
        "bbox": example["bbox"]
        .unsqueeze(0)
        .to(extractor.device),
        "pixel_values": example["pixel_values"]
        .unsqueeze(0)
        .to(extractor.device),
    }

    with torch.no_grad():
        logits = extractor.model(**inputs).logits

    prediction_ids = torch.argmax(
        logits,
        dim=-1,
    )[0].tolist()

    label_ids = example["labels"].tolist()

    predicted_labels = [
        ID_TO_LABEL[prediction_id]
        for prediction_id, label_id in zip(
            prediction_ids,
            label_ids,
            strict=True,
        )
        if label_id != -100
    ]

    true_labels = [
        ID_TO_LABEL[label_id]
        for label_id in label_ids
        if label_id != -100
    ]

    print("Predicted label distribution:")
    print(Counter(predicted_labels))

    print("\nTrue label distribution:")
    print(Counter(true_labels))

    predicted_o_ratio = (
        predicted_labels.count("O")
        / len(predicted_labels)
    )

    print(
        f"\nPredicted O ratio: {predicted_o_ratio:.2%}"
    )


if __name__ == "__main__":
    main()