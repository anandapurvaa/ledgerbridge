# tests/evaluation/test_evaluate_reconciliation_cases.py
from src.evaluation.evaluate_reconciliation_cases import (
    evaluate_reconciliation_cases,
)


def make_manifest_case(
    scenario: str,
    document_amount: float,
    ledger_amount: float,
) -> dict:
    ledger_record = {
        "invoice_id": "LB-INV-00001",
        "invoice_date": "2026-08-23",
        "vendor": "Acme Cloud Services",
        "amount": ledger_amount,
        "currency": "EUR",
        "quantity": 2,
        "fx_rate": 1.0,
        "line_items": [],
    }

    document_invoice = {
        **ledger_record,
        "amount": document_amount,
    }

    return {
        "case_id": "test-001",
        "scenario": scenario,
        "image_path": "unused.png",
        "document_invoice": document_invoice,
        "ledger_record": ledger_record,
    }


def test_reconciliation_evaluator_detects_amount_mismatch():
    manifest = [
        make_manifest_case(
            scenario="amount_mismatch",
            document_amount=250.00,
            ledger_amount=200.00,
        )
    ]

    report = evaluate_reconciliation_cases(manifest)

    assert report["summary"]["accuracy"] == 1.0

    result = report["case_results"][0]

    assert result["predicted_status"] == "amount_mismatch"
    assert result["correct"] is True