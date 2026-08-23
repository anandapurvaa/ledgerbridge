# tests/agents/test_duplicate_detection_node.py
from uuid import uuid4

from src.agents.nodes.audit_writer_node import audit_writer_node
from src.agents.nodes.duplicate_detection_node import (
    duplicate_detection_node,
)


def create_matched_state(invoice_id: str) -> dict:
    invoice = {
        "invoice_id": invoice_id,
        "invoice_date": "2026-08-23",
        "vendor": "LedgerBridge Duplicate Test Vendor",
        "amount": 250.00,
        "currency": "EUR",
        "quantity": 2,
        "fx_rate": 1.0,
        "line_items": "[]",
    }

    return {
        "user_query": "Reconcile invoice",
        "extracted_fields": invoice,
        "ledger_rows": [],
        "matched_ledger_records": [invoice],
        "unmatched_cases": [],
        "reconciliation_result": {
            "status": "matched",
            "confidence": 0.99,
            "best_match": invoice,
            "candidate_matches": [],
            "discrepancy_details": {},
        },
        "candidate_matches": [],
        "hypotheses": [],
        "dispute_letter_draft": "",
        "audit_event_id": "",
    }


def test_first_submission_is_not_duplicate_then_second_is_duplicate():
    invoice_id = f"TEST-DUP-{uuid4().hex[:12]}"
    first_state = create_matched_state(invoice_id)

    first_duplicate_result = duplicate_detection_node(first_state)

    assert first_duplicate_result[
        "reconciliation_result"
    ]["status"] == "matched"

    assert first_duplicate_result[
        "candidate_matches"
    ] == []

    audit_update = audit_writer_node(first_state)

    assert audit_update["audit_event_id"]

    second_state = create_matched_state(invoice_id)

    duplicate_update = duplicate_detection_node(second_state)

    assert duplicate_update["reconciliation_result"]["status"] == (
        "duplicate_charge"
    )

    assert duplicate_update["unmatched_cases"][0]["status"] == (
        "duplicate_charge"
    )