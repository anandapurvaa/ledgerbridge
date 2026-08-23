# src/ui/graph_runner.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.graph_builder import (
    build_reconciliation_graph,
)
from src.config import LEDGER_TABLE_ID


def run_reconciliation_graph(
    invoice_image_path: str | Path,
    user_query: str = (
        "Reconcile this invoice and create a dispute draft if a "
        "discrepancy is found."
    ),
) -> dict[str, Any]:
    """
    Run a complete reconciliation graph execution for one invoice image.
    """
    graph = build_reconciliation_graph()

    initial_state = {
        "invoice_image_path": str(invoice_image_path),
        "ledger_table_id": LEDGER_TABLE_ID,
        "user_query": user_query,
        "extracted_fields": {},
        "extraction_result": {},
        "ledger_rows": [],
        "matched_ledger_records": [],
        "unmatched_cases": [],
        "reconciliation_result": {},
        "candidate_matches": [],
        "hypotheses": [],
        "investigation": {},
        "dispute_letter_draft": "",
        "audit_event_id": "",
    }

    result = graph.invoke(initial_state)

    return {
        "extracted_fields": result.get(
            "extracted_fields",
            {},
        ),
        "reconciliation_result": result.get(
            "reconciliation_result",
            {},
        ),
        "investigation": result.get(
            "investigation",
            {},
        ),
        "dispute_letter_draft": result.get(
            "dispute_letter_draft",
            "",
        ),
        "audit_event_id": result.get(
            "audit_event_id",
            "",
        ),
        "candidate_matches": result.get(
            "candidate_matches",
            [],
        ),
    }