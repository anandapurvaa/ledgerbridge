from PIL import Image

from src.extraction.layoutlmv3_dataset import (
    create_processor,
)
from src.extraction.layoutlmv3_encoding import (
    encode_layoutlmv3_example,
)
from src.extraction.sroie_preprocessor import (
    LABEL_TO_ID,
)


def test_encoding_aligns_labels_and_removes_image_batch_dimension():
    processor = create_processor()

    example = {
        "image": Image.new(
            "RGB",
            (300, 300),
            color="white",
        ),
        "words": [
            "ACME",
            "Invoice-2026-001",
            "123.45",
        ],
        "bboxes": [
            [0, 0, 250, 100],
            [0, 120, 700, 220],
            [700, 800, 1000, 900],
        ],
        "labels": [
            LABEL_TO_ID["B-VENDOR"],
            LABEL_TO_ID["O"],
            LABEL_TO_ID["B-TOTAL"],
        ],
    }

    encoding = encode_layoutlmv3_example(
        example=example,
        processor=processor,
        max_length=32,
    )

    assert len(encoding["input_ids"]) == 32
    assert len(encoding["attention_mask"]) == 32
    assert len(encoding["bbox"]) == 32
    assert len(encoding["labels"]) == 32

    assert len(encoding["pixel_values"]) == 3
    assert len(encoding["pixel_values"][0]) == 224
    assert len(encoding["pixel_values"][0][0]) == 224

    assert encoding["labels"][0] == -100
    assert LABEL_TO_ID["B-VENDOR"] in encoding["labels"]
    assert LABEL_TO_ID["B-TOTAL"] in encoding["labels"]
    assert encoding["labels"].count(-100) > 2