# tests/evaluation/test_analyze_ocr_errors.py
from src.evaluation.analyze_ocr_errors import (
    summarize_errors,
)


def test_error_summary_counts_fields_and_failed_cases():
    case_results = [
        {
            "case_id": "matched-001",
            "scenario": "matched",
            "image_path": "one.png",
            "field_correct": {
                "invoice_id": True,
                "vendor": True,
                "amount": True,
            },
            "ground_truth": {},
            "predicted": {},
            "ocr_mean_confidence": 95.0,
        },
        {
            "case_id": "matched-002",
            "scenario": "matched",
            "image_path": "two.png",
            "field_correct": {
                "invoice_id": False,
                "vendor": True,
                "amount": False,
            },
            "ground_truth": {},
            "predicted": {},
            "ocr_mean_confidence": 80.0,
        },
    ]

    analysis = summarize_errors(case_results)

    summary = analysis["summary"]

    assert summary["total_cases"] == 2
    assert summary["fully_correct_cases"] == 1
    assert summary["failed_cases"] == 1
    assert summary["all_fields_exact_accuracy"] == 0.5
    assert summary["field_failure_counts"]["invoice_id"] == 1
    assert summary["field_failure_counts"]["amount"] == 1