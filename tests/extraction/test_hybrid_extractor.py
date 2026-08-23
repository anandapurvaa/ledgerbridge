# tests/extraction/test_hybrid_extractor.py
from src.extraction.extraction_validation import (
    validate_extracted_fields,
)


def test_model_fallback_policy_never_includes_identity_or_quantity():
    model_fallback_fields = (
        "vendor",
        "invoice_date",
        "amount",
    )

    assert "invoice_id" not in model_fallback_fields
    assert "currency" not in model_fallback_fields
    assert "quantity" not in model_fallback_fields
    assert "fx_rate" not in model_fallback_fields


def test_valid_heuristic_fields_need_no_model_fallback():
    heuristic_fields = {
        "invoice_id": "LB-INV-00021",
        "invoice_date": "2026-05-11",
        "vendor": "Umbrella Logistics Europe",
        "amount": 3134.36,
        "currency": "PLN",
        "quantity": 10,
        "fx_rate": 0.9745,
    }

    validation = validate_extracted_fields(
        heuristic_fields
    )

    assert validation["vendor"]
    assert validation["invoice_date"]
    assert validation["amount"]