# tests/agents/test_investigator.py
from src.agents.investigator import (
    investigate_reconciliation_result,
)


def test_investigator_creates_grounded_amount_summary():
    extracted_fields = {
        "invoice_id": "LB-INV-00001",
        "vendor": "Acme Cloud Services",
        "amount": 250.00,
        "currency": "EUR",
    }

    reconciliation_result = {
        "status": "amount_mismatch",
        "discrepancy_details": {
            "invoice_amount": 250.00,
            "ledger_amount": 200.00,
            "amount_delta": 50.00,
        },
    }

    investigation = investigate_reconciliation_result(
        extracted_fields,
        reconciliation_result,
    )

    assert investigation["root_cause"] == "amount_mismatch"
    assert investigation["severity"] == "high"
    assert "250.00 EUR" in investigation["summary"]
    assert "200.00 EUR" in investigation["summary"]