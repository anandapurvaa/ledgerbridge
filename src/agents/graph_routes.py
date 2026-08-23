# src/agents/graph_routes.py
from src.agents.state import AgentState


def route_after_duplicate_detection(
    state: AgentState,
) -> str:
    """
    Route all non-clean outcomes through investigation and drafting.

    `matched` can be written directly to the audit trail.
    Everything else needs either analyst context, a dispute draft,
    or at least a documented reason for no direct resolution.
    """
    status = state.get(
        "reconciliation_result",
        {},
    ).get("status", "unmatched")

    if status == "matched":
        return "write_audit"

    return "investigator"


def route_after_extractor(
    state: AgentState,
) -> str:
    """
    Prevent a failed document extraction from invoking the ledger or
    matcher with empty / invalid fields.
    """
    extracted_fields = state.get(
        "extracted_fields",
        {},
    )

    if not extracted_fields:
        return "investigator"

    required_fields = (
        "invoice_id",
        "invoice_date",
        "vendor",
        "amount",
        "currency",
        "quantity",
        "fx_rate",
    )

    if not all(
        field_name in extracted_fields
        for field_name in required_fields
    ):
        return "investigator"

    return "query_ledger"