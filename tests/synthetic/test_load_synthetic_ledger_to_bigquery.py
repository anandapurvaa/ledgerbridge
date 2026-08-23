# tests/synthetic/test_load_synthetic_ledger_to_bigquery.py
import json
from src.synthetic.load_synthetic_ledger_to_bigquery import (
    manifest_to_rows,
)


def test_manifest_rows_preserve_ledger_data():
    manifest = [
        {
            "case_id": "matched-001",
            "scenario": "matched",
            "ledger_record": {
                "invoice_id": "LB-INV-00001",
                "invoice_date": "2026-08-23",
                "vendor": "Acme Cloud Services",
                "amount": 123.45,
                "currency": "EUR",
                "quantity": 2,
                "fx_rate": 1.0,
                "line_items": [],
            },
        }
    ]

    rows = manifest_to_rows(manifest)

    assert len(rows) == 1
    assert rows[0]["case_id"] == "matched-001"
    assert rows[0]["invoice_id"] == "LB-INV-00001"
    assert rows[0]["amount"] == 123.45
    assert json.loads(rows[0]["line_items"]) == []