# src/agents/nodes/audit_writer_node.py
from uuid import uuid4

from src.agents.state import AgentState
from src.audit.reconciliation_audit_repository import (
    ReconciliationAuditRepository,
)
from src.matching.schemas import InvoiceRecord


def audit_writer_node(state: AgentState) -> dict:
    invoice = InvoiceRecord.model_validate(
        state["extracted_fields"]
    )

    reconciliation_result = state.get(
        "reconciliation_result",
        {},
    )

    status = reconciliation_result.get(
        "status",
        "unmatched",
    )

    best_match = reconciliation_result.get("best_match")

    matched_ledger_invoice_id = None

    if best_match:
        matched_ledger_invoice_id = best_match.get(
            "invoice_id"
        )

    repository = ReconciliationAuditRepository()

    audit_event_id = repository.write_event(
        invoice=invoice,
        reconciliation_status=status,
        run_id=str(uuid4()),
        source="langgraph_local",
        matched_ledger_invoice_id=matched_ledger_invoice_id,
        details=reconciliation_result.get(
            "discrepancy_details",
            {},
        ),
    )

    return {
        "audit_event_id": audit_event_id,
    }