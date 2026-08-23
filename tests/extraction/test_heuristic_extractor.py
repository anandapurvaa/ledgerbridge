from src.extraction.heuristic_extractor import (
    extract_fields_from_ocr,
    extract_fx_rate,
    extract_invoice_id,
    extract_quantity,
    extract_total,
    parse_amount,
)

def test_extract_fx_rate_from_invoice_metadata():
    assert extract_fx_rate(
        ["FX Rate: 1.0123"]
    ) == 1.0123

    assert extract_fx_rate(
        ["EXCHANGE RATE = 0.9611"]
    ) == 0.9611

    assert extract_fx_rate(
        ["Invoice Date: 2026-08-23"]
    ) == 1.0

def test_parse_amount_supports_european_and_us_formats():
    assert parse_amount("1,234.56") == 1234.56
    assert parse_amount("1.234,56") == 1234.56
    assert parse_amount("99,95") == 99.95
    assert parse_amount("99.95") == 99.95


def test_extract_invoice_id_for_ledgerbridge_format():
    text = (
        "ACME CLOUD SERVICES "
        "INVOICE "
        "Invoice No.: LB-INV-00001 "
        "Invoice Date: 2026-08-23"
    )

    assert extract_invoice_id(text) == "LB-INV-00001"


def test_extract_total_prefers_total_due_line():
    lines = [
        "Cloud support EUR 100.00",
        "Subtotal EUR 100.00",
        "Tax EUR 0.00",
        "TOTAL DUE EUR 100.00",
    ]

    assert extract_total(lines) == 100.00

def test_extract_quantity_from_inline_ocr_table_row():
    lines = [
        "Description Qty Unit Price Line Total",
        "Cloud platform support 9 112.14 € 1,009.26 €",
        "Subtotal 1,009.26 €",
        "Tax 0.00 €",
        "TOTAL DUE 1,009.26 €",
    ]

    assert extract_quantity(lines) == 9

def test_extract_quantity_from_inline_ocr_table_row():
    lines = [
        "Description Qty Unit Price Line Total",
        "Cloud platform support 9 112.14 € 1,009.26 €",
        "Subtotal 1,009.26 €",
        "Tax 0.00 €",
        "TOTAL DUE 1,009.26 €",
    ]

    assert extract_quantity(lines) == 9

def test_extract_quantity_from_qty_header_and_value():
    lines = [
        "Description Qty Unit Price Line Total",
        "Cloud platform support",
        "4",
        "EUR 100.00",
        "EUR 400.00",
    ]

    assert extract_quantity(lines) == 4


def test_heuristic_extraction_returns_graph_compatible_shape():
    ocr_result = {
        "text": (
            "ACME CLOUD SERVICES "
            "INVOICE "
            "Invoice No.: LB-INV-00001 "
            "Invoice Date: 2026-08-23 "
            "Currency EUR "
            "Description Qty Unit Price Line Total "
            "Cloud support 4 EUR 308.64 EUR 1234.56 "
            "TOTAL DUE EUR 1234.56"
        ),
        "lines": [
            "ACME CLOUD SERVICES",
            "INVOICE",
            "Invoice No.: LB-INV-00001",
            "Invoice Date: 2026-08-23",
            "Currency EUR",
            "FX Rate: 1.0123",
            "Description Qty Unit Price Line Total",
            "Cloud support",
            "4",
            "EUR 308.64",
            "EUR 1234.56",
            "TOTAL DUE EUR 1234.56",
        ],
        "mean_confidence": 96.5,
    }

    result = extract_fields_from_ocr(ocr_result)

    assert result["invoice_id"] == "LB-INV-00001"
    assert result["invoice_date"] == "2026-08-23"
    assert result["vendor"] == "ACME CLOUD SERVICES"
    assert result["amount"] == 1234.56
    assert result["currency"] == "EUR"
    assert result["quantity"] == 4
    assert result["fx_rate"] == 1.0123