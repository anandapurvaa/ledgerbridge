# tests/agents/test_resolution_drafter.py
from src.agents.resolution_drafter import (
    draft_dispute_letter,
)


def test_drafter_includes_grounded_invoice_details():
    extracted_fields = {
        "invoice_id": "LB-INV-00001",
        "invoice_date": "2026-08-23",
        "vendor": "Acme Cloud Services",
        "amount": 250.00,
        "currency": "EUR",
    }

    investigation = {
        "status": "amount_mismatch",
        "summary": "Invoice amount differs from ledger amount.",
        "dispute_reason": "Amount variance of 50.00 EUR.",
        "recommended_action": "Provide a corrected invoice.",
    }

    draft = draft_dispute_letter(
        extracted_fields,
        investigation,
    )

    assert "LB-INV-00001" in draft
    assert "Acme Cloud Services" in draft
    assert "250.00 EUR" in draft
    assert "Amount variance of 50.00 EUR." in draft


def test_drafter_returns_empty_string_for_matched_invoice():
    draft = draft_dispute_letter(
        extracted_fields={
            "invoice_id": "LB-INV-00001",
        },
        investigation={
            "status": "matched",
        },
    )

    assert draft == ""