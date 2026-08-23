from __future__ import annotations

from typing import Any

from datasets import DatasetDict, load_dataset
from transformers import AutoProcessor

from src.extraction.layoutlmv3_encoding import (
    encode_layoutlmv3_example,
)
from src.extraction.sroie_preprocessor import (
    preprocess_sroie_sample,
)

DATASET_NAME = "jsdnrs/ICDAR2019-SROIE"
BASE_MODEL_NAME = "microsoft/layoutlmv3-base"


def create_processor() -> AutoProcessor:
    return AutoProcessor.from_pretrained(
        BASE_MODEL_NAME,
        apply_ocr=False,
    )


def load_preprocessed_sroie() -> DatasetDict:
    raw_dataset = load_dataset(DATASET_NAME)

    def preprocess_batch(
        batch: dict[str, list[Any]],
    ) -> dict[str, list[Any]]:
        processed_samples = []

        for index in range(len(batch["key"])):
            sample = {
                field: batch[field][index]
                for field in batch
            }

            processed_samples.append(
                preprocess_sroie_sample(sample)
            )

        return {
            "image": [
                item["image"]
                for item in processed_samples
            ],
            "key": [
                item["key"]
                for item in processed_samples
            ],
            "words": [
                item["words"]
                for item in processed_samples
            ],
            "bboxes": [
                item["bboxes"]
                for item in processed_samples
            ],
            "labels": [
                item["labels"]
                for item in processed_samples
            ],
            "entities": [
                item["entities"]
                for item in processed_samples
            ],
        }

    return raw_dataset.map(
        preprocess_batch,
        batched=True,
        remove_columns=raw_dataset["train"].column_names,
        desc="Preprocessing SROIE fields and boxes",
        load_from_cache_file=False,
    )


def create_encoded_sroie(
    max_length: int = 512,
) -> DatasetDict:
    dataset = load_preprocessed_sroie()
    processor = create_processor()

    def encode_example(
        example: dict[str, Any],
    ) -> dict[str, Any]:
        return encode_layoutlmv3_example(
            example=example,
            processor=processor,
            max_length=max_length,
        )

    encoded_dataset = dataset.map(
        encode_example,
        remove_columns=dataset["train"].column_names,
        desc="Encoding SROIE for LayoutLMv3",
        load_from_cache_file=False,
    )

    required_columns = [
        "input_ids",
        "attention_mask",
        "bbox",
        "pixel_values",
        "labels",
    ]

    encoded_dataset.set_format(
        type="torch",
        columns=required_columns,
    )

    return encoded_dataset