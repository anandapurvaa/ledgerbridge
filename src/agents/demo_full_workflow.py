# src/agents/demo_full_workflow.py
from __future__ import annotations

import json
from pathlib import Path

from src.agents.graph_builder import (
    build_reconciliation_graph,
)


PROJECT_ID = "cloudprojects-506123"

SYNTHETIC_LEDGER_TABLE = (
    f"{PROJECT_ID}."
    "ledgerbridge."
    "synthetic_evaluation_ledger"
)

DEMO_IMAGE = Path(
    "data/synthetic/invoice_images/"
    "amount_mismatch_00023.png"
)


def initial_state() -> dict:
    return {
        "invoice_image_path": str(DEMO_IMAGE),
        "ledger_table_id": SYNTHETIC_LEDGER_TABLE,
        "user_query": (
            "Reconcile this invoice and create a dispute "
            "draft if a discrepancy is found."
        ),
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


def main() -> None:
    if not DEMO_IMAGE.exists():
        raise FileNotFoundError(
            f"Demo image not found: {DEMO_IMAGE}\n"
            "Run synthetic invoice generation first."
        )

    graph = build_reconciliation_graph()

    result = graph.invoke(initial_state())

    printable_result = {
        "extracted_fields": result[
            "extracted_fields"
        ],
        "reconciliation_result": result[
            "reconciliation_result"
        ],
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
    }

    print(
        json.dumps(
            printable_result,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()