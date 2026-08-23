# tests/extraction/test_ledger_aware_repair.py
from src.extraction.ledger_aware_repair import (
    repair_extracted_fields,
)


def base_extracted_fields() -> dict:
    return {
        "invoice_id": "LB-INV-00009",
        "invoice_date": "2026-06-23",
        "vendor": "Umbrella Logistics Europe",
        "amount": 1653.67,
        "currency": "PLN",
        "quantity": 1,
        "fx_rate": 1.0,
        "line_items": [],
        "extraction_metadata": {},
    }


def base_ledger_record() -> dict:
    return {
        "invoice_id": "LB-INV-00009",
        "invoice_date": "2026-06-23",
        "vendor": "Umbrella Logistics Europe",
        "amount": 653.67,
        "currency": "PLN",
        "quantity": 11,
        "fx_rate": 0.9611,
        "line_items": [],
    }


def test_repairs_numeric_prefix_amount_corruption():
    repaired = repair_extracted_fields(
        extracted_fields=base_extracted_fields(),
        ledger_candidate=base_ledger_record(),
    )

    assert repaired["amount"] == 653.67

    repairs = repaired["extraction_metadata"][
        "ledger_aware_repairs"
    ]

    assert repairs[0]["field"] == "amount"


def test_repairs_quantity_fallback_to_one():
    repaired = repair_extracted_fields(
        extracted_fields=base_extracted_fields(),
        ledger_candidate=base_ledger_record(),
    )

    assert repaired["quantity"] == 11

    repair_fields = {
        repair["field"]
        for repair in repaired["extraction_metadata"][
            "ledger_aware_repairs"
        ]
    }

    assert "quantity" in repair_fields


def test_does_not_overwrite_normal_amount_difference():
    extracted = base_extracted_fields()
    extracted["amount"] = 691.17

    repaired = repair_extracted_fields(
        extracted_fields=extracted,
        ledger_candidate=base_ledger_record(),
    )

    assert repaired["amount"] == 691.17

    amount_repairs = [
        repair
        for repair in repaired["extraction_metadata"][
            "ledger_aware_repairs"
        ]
        if repair["field"] == "amount"
    ]

    assert amount_repairs == []


def test_no_candidate_means_no_repair():
    extracted = base_extracted_fields()

    repaired = repair_extracted_fields(
        extracted_fields=extracted,
        ledger_candidate=None,
    )

    assert repaired["amount"] == 1653.67
    assert repaired["quantity"] == 1