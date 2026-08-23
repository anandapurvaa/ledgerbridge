# tests/evaluation/test_evaluate_ocr_extraction.py
from src.evaluation.evaluate_ocr_extraction import (
    normalize_text,
)


def test_normalize_text_removes_case_and_formatting_noise():
    assert normalize_text("Acme Cloud Services") == (
        "acme cloud services"
    )

    assert normalize_text("ACME, CLOUD. SERVICES") == (
        "acme cloud services"
    )