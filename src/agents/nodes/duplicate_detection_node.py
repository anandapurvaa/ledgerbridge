# src/agents/nodes/duplicate_detection_node.py
from src.agents.state import AgentState
from src.audit.reconciliation_audit_repository import (
    ReconciliationAuditRepository,
)
from src.matching.schemas import InvoiceRecord


def duplicate_detection_node(state: AgentState) -> dict:
    """
    Check whether a successfully matched invoice was reconciled before.

    Non-matched outcomes pass through unchanged. Candidate match data is
    always preserved so the operator console can display it.
    """
    reconciliation_result = state.get(
        "reconciliation_result",
        {},
    )

    candidate_matches = state.get(
        "candidate_matches",
        reconciliation_result.get(
            "candidate_matches",
            [],
        ),
    )

    status = reconciliation_result.get(
        "status",
        "unmatched",
    )

    # The matcher has already classified any mismatch or ambiguity.
    # Do not run duplicate checks for those outcomes.
    if status != "matched":
        return {
            "reconciliation_result": {
                **reconciliation_result,
                "candidate_matches": candidate_matches,
            },
            "candidate_matches": candidate_matches,
        }

    invoice = InvoiceRecord.model_validate(
        state["extracted_fields"]
    )

    repository = ReconciliationAuditRepository()

    prior_event = repository.find_prior_successful_invoice(
        invoice
    )

    # First successful reconciliation: preserve the match and candidates.
    if not prior_event:
        return {
            "reconciliation_result": {
                **reconciliation_result,
                "candidate_matches": candidate_matches,
            },
            "candidate_matches": candidate_matches,
        }

    updated_result = {
        **reconciliation_result,
        "status": "duplicate_charge",
        "confidence": 1.0,
        "candidate_matches": candidate_matches,
        "discrepancy_details": {
            "reason": (
                "An identical invoice was previously reconciled "
                "successfully and recorded in the audit trail."
            ),
            "prior_audit_event_id": prior_event[
                "audit_event_id"
            ],
            "prior_event_timestamp": str(
                prior_event["event_timestamp"]
            ),
            "prior_run_id": prior_event["run_id"],
        },
    }

    unmatched_case = {
        "invoice": invoice.model_dump(),
        "status": "duplicate_charge",
        "confidence": 1.0,
        "details": updated_result["discrepancy_details"],
    }

    return {
        "matched_ledger_records": [],
        "unmatched_cases": [unmatched_case],
        "reconciliation_result": updated_result,
        "candidate_matches": candidate_matches,
    }