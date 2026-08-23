# tests/synthetic/test_generate_invoice_image_dataset.py
from src.synthetic.generate_invoice_image_dataset import (
    build_dataset,
)


def test_generated_dataset_has_all_reconciliation_scenarios():
    manifest = build_dataset(
        records_per_scenario=2,
        seed=42,
    )

    assert len(manifest) == 10

    scenarios = [
        item["scenario"]
        for item in manifest
    ]

    assert scenarios.count("matched") == 2
    assert scenarios.count("amount_mismatch") == 2
    assert scenarios.count("fx_mismatch") == 2
    assert scenarios.count("quantity_mismatch") == 2
    assert scenarios.count("duplicate_charge") == 2


def test_amount_mismatch_changes_document_only():
    manifest = build_dataset(
        records_per_scenario=1,
        seed=42,
    )

    amount_case = next(
        item
        for item in manifest
        if item["scenario"] == "amount_mismatch"
    )

    assert (
        amount_case["document_invoice"]["amount"]
        != amount_case["ledger_record"]["amount"]
    )

    assert (
        amount_case["document_invoice"]["invoice_id"]
        == amount_case["ledger_record"]["invoice_id"]
    )