from __future__ import annotations

from typing import Any

from transformers import AutoProcessor


def remove_single_batch_dimension(
    value: Any,
) -> Any:
    """
    The processor receives one image but returns image features with a
    leading batch dimension: [1, 3, 224, 224].

    Hugging Face Dataset examples must store one image as:
    [3, 224, 224].

    The Trainer's data loader will add the true batch dimension later.
    """
    if hasattr(value, "tolist"):
        value = value.tolist()

    if isinstance(value, list) and len(value) == 1:
        return value[0]

    return value


def encode_layoutlmv3_example(
    example: dict[str, Any],
    processor: AutoProcessor,
    max_length: int = 512,
) -> dict[str, Any]:
    """
    Encode one preprocessed SROIE record.

    The dataset stores:
      input_ids:       [max_length]
      attention_mask:  [max_length]
      bbox:            [max_length, 4]
      pixel_values:    [3, 224, 224]
      labels:          [max_length]

    The data loader later converts them to:
      input_ids:       [batch, max_length]
      bbox:            [batch, max_length, 4]
      pixel_values:    [batch, 3, 224, 224]
      labels:          [batch, max_length]
    """
    encoding = processor(
        images=example["image"],
        text=example["words"],
        boxes=example["bboxes"],
        truncation=True,
        padding="max_length",
        max_length=max_length,
        return_tensors="pt",
    )

    word_ids = encoding.word_ids(batch_index=0)

    aligned_labels: list[int] = []
    previous_word_id: int | None = None

    for word_id in word_ids:
        if word_id is None:
            aligned_labels.append(-100)

        elif word_id != previous_word_id:
            aligned_labels.append(
                int(example["labels"][word_id])
            )

        else:
            aligned_labels.append(-100)

        previous_word_id = word_id

    encoded_example: dict[str, Any] = {}

    for key, value in encoding.items():
        encoded_example[key] = remove_single_batch_dimension(
            value
        )

    encoded_example["labels"] = aligned_labels

    return encoded_example