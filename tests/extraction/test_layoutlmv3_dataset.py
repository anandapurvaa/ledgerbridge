# tests/extraction/test_layoutlmv3_dataset.py
from src.extraction.layoutlmv3_dataset import (
    create_processor,
)
from src.extraction.sroie_preprocessor import (
    LABEL_LIST,
)


def test_layoutlmv3_processor_can_load():
    processor = create_processor()

    assert processor is not None


def test_label_list_has_expected_classes():
    assert LABEL_LIST == [
        "O",
        "B-VENDOR",
        "I-VENDOR",
        "B-DATE",
        "I-DATE",
        "B-TOTAL",
        "I-TOTAL",
    ]