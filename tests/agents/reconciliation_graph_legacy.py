# tests/agents/test_reconciliation_graph.py
from copy import deepcopy

from src.agents.graph_builder import build_reconciliation_graph
from src.agents.nodes.query_ledger_node import call_query_ledger


PROJECT_ID = "cloudprojects-506123"
TABLE_ID = f"{PROJECT_ID}.ledgerbridge.invoices"


def blank_state(extracted_fields: dict) -> dict:
    return {
        "user_query": "Reconcile an invoice against the ledger.",
        "extracted_fields": extracted_fields,
        "ledger_rows": [],
        "matched_ledger_records": [],
        "unmatched_cases": [],
        "reconciliation_result": {},
        "candidate_matches": [],
        "hypotheses": [],
        "dispute_letter_draft": "",
    }


def test_known_ledger_record_is_matched():
    graph = build_reconciliation_graph()

    initial_state = blank_state(
        {
            "invoice_id": "INV-00001",
            "invoice_date": "2026-01-01",
            "vendor": "Acme Corp",
            "amount": 100.00,
            "currency": "EUR",
            "quantity": 1,
            "fx_rate": 1.0,
            "line_items": "[]",
        }
    )

    # This test replaces the placeholder invoice with a real ledger row.
    # It means it does not depend on random ledger values.
    import asyncio

    rows = asyncio.run(
        call_query_ledger(
            f"""
            SELECT
                invoice_id,
                invoice_date,
                vendor,
                amount,
                currency,
                quantity,
                fx_rate,
                line_items
            FROM `{TABLE_ID}`
            LIMIT 1
            """
        )
    )

    assert rows, "Expected at least one record in the ledger table."

    initial_state["extracted_fields"] = rows[0]

    result = graph.invoke(initial_state)

    assert result["reconciliation_result"]["status"] == "matched"
    assert result["matched_ledger_records"]
    assert result["unmatched_cases"] == []


def test_quantity_error_is_flagged():
    graph = build_reconciliation_graph()

    import asyncio

    rows = asyncio.run(
        call_query_ledger(
            f"""
            SELECT
                invoice_id,
                invoice_date,
                vendor,
                amount,
                currency,
                quantity,
                fx_rate,
                line_items
            FROM `{TABLE_ID}`
            LIMIT 1
            """
        )
    )

    assert rows, "Expected at least one record in the ledger table."

    altered_invoice = deepcopy(rows[0])
    altered_invoice["quantity"] = int(altered_invoice["quantity"]) + 2
    altered_invoice["amount"] = round(float(altered_invoice["amount"]) * 1.10, 2)

    result = graph.invoke(blank_state(altered_invoice))

    assert result["reconciliation_result"]["status"] == "quantity_mismatch"
    assert result["unmatched_cases"]