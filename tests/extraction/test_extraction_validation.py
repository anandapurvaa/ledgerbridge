# tests/extraction/test_extraction_validation.py
from src.extraction.extraction_validation import (
    validate_extracted_fields,
)


def test_validation_accepts_complete_invoice_schema():
    result = validate_extracted_fields(
        {
            "invoice_id": "LB-INV-00001",
            "vendor": "Acme Cloud Services",
            "invoice_date": "2026-08-23",
            "amount": 1234.56,
            "currency": "EUR",
            "quantity": 4,
            "fx_rate": 1.0,
        }
    )

    assert all(result.values())


def test_validation_rejects_unknown_placeholder_values():
    result = validate_extracted_fields(
        {
            "invoice_id": "UNKNOWN-INVOICE-ID",
            "vendor": "UNKNOWN-VENDOR",
            "invoice_date": "not-a-date",
            "amount": 0,
            "currency": "INVALID",
            "quantity": 0,
            "fx_rate": 0,
        }
    )

    assert not any(result.values())