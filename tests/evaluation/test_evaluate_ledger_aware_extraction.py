# tests/evaluation/test_evaluate_ledger_aware_extraction.py
from src.evaluation.evaluate_ledger_aware_extraction import (
    compare_fields,
)


def test_compare_fields_accepts_close_amounts():
    predicted = {
        "invoice_id": "LB-INV-00001",
        "invoice_date": "2026-08-23",
        "vendor": "Acme Cloud Services",
        "amount": 123.45,
        "currency": "EUR",
        "quantity": 2,
    }

    ground_truth = {
        **predicted,
        "amount": 123.46,
    }

    comparisons = compare_fields(
        predicted=predicted,
        ground_truth=ground_truth,
    )

    assert all(comparisons.values())