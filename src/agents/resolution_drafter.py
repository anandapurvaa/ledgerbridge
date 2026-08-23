# src/agents/resolution_drafter.py
from __future__ import annotations

from typing import Any


def draft_dispute_letter(
    extracted_fields: dict[str, Any],
    investigation: dict[str, Any],
) -> str:
    """
    Create a deterministic vendor-facing draft.

    This is intentionally a draft only. It must be reviewed and
    approved by a human in the future UI before any sending action.
    """
    status = investigation.get("status", "unmatched")

    if status in {"matched", "no_action_required"}:
        return ""

    vendor = extracted_fields.get(
        "vendor",
        "Vendor",
    )

    invoice_id = extracted_fields.get(
        "invoice_id",
        "the referenced invoice",
    )

    invoice_date = extracted_fields.get(
        "invoice_date",
        "the invoice date",
    )

    amount = extracted_fields.get(
        "amount",
        0.0,
    )

    currency = extracted_fields.get(
        "currency",
        "EUR",
    )

    summary = investigation.get(
        "summary",
        "A discrepancy was identified during reconciliation.",
    )

    dispute_reason = investigation.get(
        "dispute_reason",
        "Please review the invoice details.",
    )

    recommended_action = investigation.get(
        "recommended_action",
        "Please provide clarification.",
    )

    return f"""Subject: Request for clarification — Invoice {invoice_id}

Dear {vendor} Accounts Receivable Team,

During our reconciliation review, we identified a discrepancy relating to invoice {invoice_id}, dated {invoice_date}, for {amount:,.2f} {currency}.

{summary}

Reason for review: {dispute_reason}

Please review the invoice and provide supporting documentation, confirmation, or a corrected invoice as appropriate.

Requested next step: {recommended_action}

We will keep the invoice under review until the discrepancy is resolved.

Kind regards,
LedgerBridge Finance Operations
"""