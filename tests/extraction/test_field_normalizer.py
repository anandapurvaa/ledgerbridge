# tests/extraction/test_field_normalizer.py
from src.extraction.entity_decoder import EntitySpan
from src.extraction.field_normalizer import (
    normalize_amount,
    normalize_date,
    normalize_layoutlmv3_output,
)


def test_normalize_amount_supports_common_formats():
    assert normalize_amount("TOTAL RM 9.00") == 9.00
    assert normalize_amount("EUR 1,234.56") == 1234.56
    assert normalize_amount("EUR 1.234,56") == 1234.56


def test_normalize_date_supports_common_formats():
    assert normalize_date("25/12/2018") == "2018-12-25"
    assert normalize_date("05 MAR 2018") == "2018-03-05"
    assert normalize_date("2018-12-25 08:13") == "2018-12-25"


def test_normalizer_maps_spans_to_ledgerbridge_contract():
    spans = [
        EntitySpan(
            entity_type="VENDOR",
            text="ACME CLOUD SERVICES",
            score=0.92,
            start_word=0,
            end_word=2,
        ),
        EntitySpan(
            entity_type="DATE",
            text="2026-08-23",
            score=0.91,
            start_word=3,
            end_word=3,
        ),
        EntitySpan(
            entity_type="TOTAL",
            text="TOTAL EUR 1234.56",
            score=0.94,
            start_word=4,
            end_word=6,
        ),
    ]

    result = normalize_layoutlmv3_output(
        spans=spans,
        raw_text=" ".join(
            [
                "ACME",
                "CLOUD",
                "SERVICES",
                "2026-08-23",
                "TOTAL",
                "EUR",
                "1234.56",
            ]
        ),
    )

    assert result["vendor"] == "ACME CLOUD SERVICES"
    assert result["invoice_date"] == "2026-08-23"
    assert result["amount"] == 1234.56
    assert result["currency"] == "EUR"
    assert result["quantity"] == 1
    assert result["fx_rate"] == 1.0