# src/ui/graph_runner.py
from __future__ import annotations

import time
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
    t_start = time.time()

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

    # Time the full graph execution (OCR + extraction + matching + investigation + draft + audit)
    t_graph_start = time.time()
    result = graph.invoke(initial_state)
    t_graph_end = time.time()

    print(
        f"[PROFILE] graph.invoke (full pipeline) took "
        f"{t_graph_end - t_graph_start:.2f}s for {Path(invoice_image_path).name}"
    )

    # If you want to add more granular timing later, do it inside the graph nodes
    # (extractor_node, matcher_node, investigation_node, draft_node, audit_writer_node).

    t_end = time.time()
    print(f"[PROFILE] total run_reconciliation_graph: {t_end - t_start:.2f}s")

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