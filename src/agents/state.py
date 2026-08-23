from typing import Any

from typing_extensions import TypedDict


class AgentState(TypedDict):
    user_query: str

    # Invoice image input and structured extraction output.
    invoice_image_path: str
    extracted_fields: dict[str, Any]
    extraction_result: dict[str, Any]

    # Optional per-run ledger source.
    ledger_table_id: str

    # Data returned from the ledger query node.
    ledger_rows: list[dict[str, Any]]

    # Matching and reconciliation outputs.
    matched_ledger_records: list[dict[str, Any]]
    unmatched_cases: list[dict[str, Any]]
    reconciliation_result: dict[str, Any]
    candidate_matches: list[dict[str, Any]]

    # Investigation and resolution-drafting outputs.
    hypotheses: list[str]
    investigation: dict[str, Any]
    dispute_letter_draft: str

    # Audit output.
    audit_event_id: str