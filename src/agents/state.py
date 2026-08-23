from typing import Any

from typing_extensions import TypedDict


class AgentState(TypedDict):
    user_query: str

    # Structured invoice fields. For now these are synthetic/manual.
    # The Extractor node will populate this later from an image.
    extracted_fields: dict[str, Any]

    # Data returned from the ledger MCP tool.
    ledger_rows: list[dict[str, Any]]

    # Matching output.
    matched_ledger_records: list[dict[str, Any]]
    unmatched_cases: list[dict[str, Any]]
    reconciliation_result: dict[str, Any]

    # Future Investigator and Resolution-Drafter outputs.
    hypotheses: list[str]
    dispute_letter_draft: str
    audit_event_id: str
    invoice_image_path: str
    extraction_result: dict[str, Any]