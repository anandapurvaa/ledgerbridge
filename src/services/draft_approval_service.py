from __future__ import annotations

from src.audit.draft_approval_repository import (
    DraftApprovalRepository,
)
from src.config import (
    DEFAULT_REVIEWER_ID,
    ENVIRONMENT,
)


def approve_draft_for_review(
    draft: str,
    audit_event_id: str,
    invoice_id: str,
    reconciliation_status: str,
    reviewer_id: str = DEFAULT_REVIEWER_ID,
) -> str:
    """
    Validate and persist an approval for a review.

    Only one open review is allowed per invoice in each environment.
    No communication is sent to the vendor.
    """
    if not draft or not draft.strip():
        raise ValueError(
            "Cannot approve an empty dispute draft."
        )

    if not audit_event_id or not audit_event_id.strip():
        raise ValueError(
            "Cannot approve without an audit event ID."
        )

    if not invoice_id or not invoice_id.strip():
        raise ValueError(
            "Cannot approve a draft without an invoice ID."
        )

    repository = DraftApprovalRepository()

    existing_review = repository.find_open_review(
        invoice_id=invoice_id.strip(),
        environment=ENVIRONMENT,
    )

    if existing_review:
        approved_at = existing_review.get(
            "approved_at",
            "an earlier time",
        )
        reviewer = existing_review.get(
            "reviewer_id",
            "another reviewer",
        )
        approval_event_id = existing_review.get(
            "approval_event_id",
            "unknown",
        )

        raise ValueError(
            "A review is already open for invoice "
            f"{invoice_id}. It was approved by {reviewer} "
            f"at {approved_at}. "
            f"Existing approval event ID: {approval_event_id}."
        )

    return repository.record_approval(
        reconciliation_audit_event_id=audit_event_id.strip(),
        invoice_id=invoice_id.strip(),
        reconciliation_status=reconciliation_status or "",
        final_draft=draft.strip(),
        reviewer_id=reviewer_id,
        environment=ENVIRONMENT,
    )