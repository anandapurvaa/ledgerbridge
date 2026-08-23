# src/agents/nodes/matcher_node.py
from src.agents.state import AgentState
from src.matching.embedding_matcher import LedgerEmbeddingMatcher
from src.matching.reconciliation_rules import classify_reconciliation
from src.matching.schemas import InvoiceRecord


def matcher_node(state: AgentState) -> dict:
    extracted_fields = state.get("extracted_fields", {})
    ledger_rows = state.get("ledger_rows", [])

    if not extracted_fields:
        return {
            "matched_ledger_records": [],
            "unmatched_cases": [],
            "reconciliation_result": {
                "status": "unmatched",
                "confidence": 1.0,
                "discrepancy_details": {
                    "reason": "No extracted invoice fields were provided."
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
                    "reason": "No ledger rows were available for matching."
                },
            },
        }

    invoice = InvoiceRecord.model_validate(extracted_fields)

    matcher = LedgerEmbeddingMatcher()
    matcher.build_index(ledger_rows)

    candidates = matcher.search(invoice, top_k=5)
    result = classify_reconciliation(invoice, candidates)

    candidate_dicts = [
        {
            "rank": candidate.rank,
            "semantic_score": candidate.semantic_score,
            "ledger_record": candidate.ledger_record.model_dump(),
        }
        for candidate in candidates
    ]

    result_dict = result.model_dump()

    if result.status == "matched":
        matched_records = [result.best_match.model_dump()] if result.best_match else []
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
        "matched_ledger_records": matched_records,
        "unmatched_cases": unmatched_cases,
        "reconciliation_result": result_dict,
        "candidate_matches": candidate_dicts,
    }