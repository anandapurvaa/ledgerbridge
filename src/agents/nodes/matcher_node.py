from __future__ import annotations

from typing import Any

from src.agents.state import AgentState
from src.evaluation.evaluate_true_end_to_end import (
    find_invoice_id_candidate,
    prioritize_identity_candidate,
)
from src.extraction.ledger_aware_repair import (
    repair_extracted_fields,
)
from src.matching.embedding_matcher import (
    LedgerEmbeddingMatcher,
)
from src.matching.reconciliation_rules import (
    classify_reconciliation,
)
from src.matching.schemas import InvoiceRecord


def matcher_node(state: AgentState) -> dict:
    """
    Reconcile extracted invoice fields against BigQuery ledger rows.

    Resolution order:
      1. Find exact invoice-ID candidate when available.
      2. Apply conservative ledger-aware OCR repair.
      3. Retrieve semantic candidates through FAISS.
      4. Place deterministic identity candidate before FAISS candidates.
      5. Apply finance-aware reconciliation rules.
    """
    extracted_fields = state.get(
        "extracted_fields",
        {},
    )

    ledger_rows = state.get(
        "ledger_rows",
        [],
    )

    if not extracted_fields:
        return {
            "matched_ledger_records": [],
            "unmatched_cases": [],
            "reconciliation_result": {
                "status": "unmatched",
                "confidence": 1.0,
                "discrepancy_details": {
                    "reason": (
                        "No extracted invoice fields were provided."
                    )
                },
            },
        }

    if not ledger_rows:
        return {
            "matched_ledger_records": [],
            "unmatched_cases": [],
            "reconciliation_result": {
                "status": "unmatched",
                "confidence": 1.0,
                "discrepancy_details": {
                    "reason": (
                        "No ledger rows were available for matching."
                    )
                },
            },
        }

    identity_candidate = find_invoice_id_candidate(
        extracted_fields=extracted_fields,
        ledger_rows=ledger_rows,
    )

    repaired_fields = repair_extracted_fields(
        extracted_fields=extracted_fields,
        ledger_candidate=identity_candidate,
    )

    invoice = InvoiceRecord.model_validate(
        repaired_fields
    )

    matcher = LedgerEmbeddingMatcher()
    matcher.build_index(ledger_rows)

    candidates = matcher.search(
        invoice=invoice,
        top_k=5,
    )

    candidates = prioritize_identity_candidate(
        ledger_candidate=identity_candidate,
        candidates=candidates,
    )

    result = classify_reconciliation(
        invoice=invoice,
        candidates=candidates,
    )

    candidate_dicts = [
        {
            "rank": candidate.rank,
            "semantic_score": candidate.semantic_score,
            "ledger_record": candidate.ledger_record.model_dump(),
        }
        for candidate in candidates
    ]

    result_dict = result.model_dump()

    # Record repair evidence in the result, not only the extracted fields.
    result_dict["ocr_repair_log"] = repaired_fields.get(
        "extraction_metadata",
        {},
    ).get("ledger_aware_repairs", [])

    if result.status == "matched":
        matched_records = [
            result.best_match.model_dump()
        ] if result.best_match else []

        unmatched_cases = []

    else:
        matched_records = []

        unmatched_cases = [
            {
                "invoice": invoice.model_dump(),
                "status": result.status,
                "confidence": result.confidence,
                "details": result.discrepancy_details,
            }
        ]

    return {
        # Important: persist repaired values for downstream investigation,
        # drafting, and audit writing.
        "extracted_fields": repaired_fields,
        "matched_ledger_records": matched_records,
        "unmatched_cases": unmatched_cases,
        "reconciliation_result": result_dict,
        "candidate_matches": candidate_dicts,
    }