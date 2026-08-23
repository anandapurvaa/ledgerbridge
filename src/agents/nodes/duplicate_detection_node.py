# src/agents/nodes/duplicate_detection_node.py
from uuid import uuid4

from src.agents.state import AgentState
from src.audit.reconciliation_audit_repository import (
    ReconciliationAuditRepository,
)
from src.matching.schemas import InvoiceRecord


def duplicate_detection_node(state: AgentState) -> dict:
    """
    Run only after the matcher has produced `matched`.

    A first valid invoice stays matched.
    A later identical successful invoice becomes duplicate_charge.
    """
    reconciliation_result = state.get("reconciliation_result", {})

    if reconciliation_result.get("status") != "matched":
        return {}

    invoice = InvoiceRecord.model_validate(
        state["extracted_fields"]
    )

    repository = ReconciliationAuditRepository()

    prior_event = repository.find_prior_successful_invoice(
        invoice
    )

    if prior_event:
        updated_result = {
            **reconciliation_result,
            "status": "duplicate_charge",
            "confidence": 1.0,
            "discrepancy_details": {
                "reason": (
                    "An identical invoice was previously reconciled "
                    "successfully and recorded in the audit trail."
                ),
                "prior_audit_event_id": prior_event["audit_event_id"],
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
        }

    return {}