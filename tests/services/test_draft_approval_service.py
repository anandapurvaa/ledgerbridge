import pytest

from src.services.draft_approval_service import (
    approve_draft_for_review,
)


def test_approval_rejects_empty_draft():
    with pytest.raises(
        ValueError,
        match="empty dispute draft",
    ):
        approve_draft_for_review(
            draft="",
            audit_event_id="audit-event-1",
            invoice_id="LB-INV-00001",
            reconciliation_status="amount_mismatch",
        )


def test_approval_rejects_empty_audit_event_id():
    with pytest.raises(
        ValueError,
        match="audit event ID",
    ):
        approve_draft_for_review(
            draft="A valid dispute draft.",
            audit_event_id="",
            invoice_id="LB-INV-00001",
            reconciliation_status="amount_mismatch",
        )


def test_approval_rejects_empty_invoice_id():
    with pytest.raises(
        ValueError,
        match="invoice ID",
    ):
        approve_draft_for_review(
            draft="A valid dispute draft.",
            audit_event_id="audit-event-1",
            invoice_id="",
            reconciliation_status="amount_mismatch",
        )


def test_approval_rejects_existing_open_review(
    monkeypatch,
):
    class FakeRepository:
        def find_open_review(
            self,
            invoice_id: str,
            environment: str,
        ):
            return {
                "approval_event_id": "existing-approval-1",
                "approved_at": "2026-08-23 18:00:00+00:00",
                "reviewer_id": "demo_operator",
            }

    monkeypatch.setattr(
        "src.services.draft_approval_service."
        "DraftApprovalRepository",
        FakeRepository,
    )

    with pytest.raises(
        ValueError,
        match="already open",
    ):
        approve_draft_for_review(
            draft="A valid dispute draft.",
            audit_event_id="audit-event-1",
            invoice_id="LB-INV-00001",
            reconciliation_status="amount_mismatch",
        )


def test_approval_persists_trimmed_draft(
    monkeypatch,
):
    class FakeRepository:
        def __init__(self):
            self.recorded_arguments = None

        def find_open_review(
            self,
            invoice_id: str,
            environment: str,
        ):
            return None

        def record_approval(self, **kwargs):
            self.recorded_arguments = kwargs
            return "approval-event-123"

    repository = FakeRepository()

    monkeypatch.setattr(
        "src.services.draft_approval_service."
        "DraftApprovalRepository",
        lambda: repository,
    )

    result = approve_draft_for_review(
        draft="  Final edited dispute draft.  ",
        audit_event_id=" audit-event-1 ",
        invoice_id=" LB-INV-00001 ",
        reconciliation_status="amount_mismatch",
        reviewer_id="tester",
    )

    assert result == "approval-event-123"

    assert repository.recorded_arguments[
        "reconciliation_audit_event_id"
    ] == "audit-event-1"

    assert repository.recorded_arguments[
        "invoice_id"
    ] == "LB-INV-00001"

    assert repository.recorded_arguments[
        "final_draft"
    ] == "Final edited dispute draft."

    assert repository.recorded_arguments[
        "reviewer_id"
    ] == "tester"