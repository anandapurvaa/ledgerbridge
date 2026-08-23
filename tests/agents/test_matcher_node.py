# tests/agents/test_matcher_node.py
from src.agents.nodes.matcher_node import matcher_node


def test_matcher_prioritizes_exact_invoice_id_over_faiss():
    state = {
        "extracted_fields": {
            "invoice_id": "LB-INV-00022",
            "invoice_date": "2026-06-18",
            "vendor": "Stark Industrial Supply",
            "amount": 450.30,
            "currency": "PLN",
            "quantity": 3,
            "fx_rate": 0.8775,
            "line_items": [],
            "extraction_metadata": {},
        },
        "ledger_rows": [
            {
                "invoice_id": "LB-INV-00053",
                "invoice_date": "2026-03-20",
                "vendor": "Stark Industrial Supply",
                "amount": 246.41,
                "currency": "PLN",
                "quantity": 1,
                "fx_rate": 0.9798,
                "line_items": [],
            },
            {
                "invoice_id": "LB-INV-00022",
                "invoice_date": "2026-06-18",
                "vendor": "Stark Industrial Supply",
                "amount": 412.80,
                "currency": "PLN",
                "quantity": 3,
                "fx_rate": 0.8775,
                "line_items": [],
            },
        ],
    }

    result = matcher_node(state)

    assert result["reconciliation_result"]["status"] == (
        "amount_mismatch"
    )

    assert result["reconciliation_result"][
        "best_match"
    ]["invoice_id"] == "LB-INV-00022"