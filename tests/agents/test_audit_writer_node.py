from unittest.mock import Mock

from src.agents.nodes.audit_writer_node import (
    audit_writer_node,
)


def complete_extracted_fields() -> dict:
    return {
        "invoice_id": "LB-INV-00001",
        "invoice_date": "2026-01-10",
        "vendor": "Acme Cloud Services",
        "amount": 100.0,
        "currency": "EUR",
        "quantity": 1,
        "fx_rate": 1.0,
        "line_items": [],
    }


def test_audit_writer_returns_repository_event_id(
    monkeypatch,
):
    repository = Mock()
    repository.write_event.return_value = (
        "audit-event-123"
    )

    monkeypatch.setattr(
        "src.agents.nodes.audit_writer_node."
        "ReconciliationAuditRepository",
        lambda: repository,
    )

    state = {
        "extracted_fields": complete_extracted_fields(),
        "reconciliation_result": {
            "status": "amount_mismatch",
            "best_match": {
                "invoice_id": "LB-INV-00001",
            },
            "discrepancy_details": {
                "amount_delta": 37.50,
            },
        },
    }

    result = audit_writer_node(state)

    assert result == {
        "audit_event_id": "audit-event-123",
    }

    repository.write_event.assert_called_once()

    call_kwargs = repository.write_event.call_args.kwargs

    assert call_kwargs["reconciliation_status"] == (
        "amount_mismatch"
    )

    assert call_kwargs["matched_ledger_invoice_id"] == (
        "LB-INV-00001"
    )

    assert call_kwargs["details"] == {
        "amount_delta": 37.50,
    }

    assert call_kwargs["source"] == "langgraph_local"


def test_audit_writer_handles_no_best_match(
    monkeypatch,
):
    repository = Mock()
    repository.write_event.return_value = (
        "audit-event-unmatched"
    )

    monkeypatch.setattr(
        "src.agents.nodes.audit_writer_node."
        "ReconciliationAuditRepository",
        lambda: repository,
    )

    state = {
        "extracted_fields": complete_extracted_fields(),
        "reconciliation_result": {
            "status": "unmatched",
            "discrepancy_details": {
                "reason": "No ledger candidates found.",
            },
        },
    }

    result = audit_writer_node(state)

    assert result["audit_event_id"] == (
        "audit-event-unmatched"
    )

    call_kwargs = repository.write_event.call_args.kwargs

    assert call_kwargs["matched_ledger_invoice_id"] is None
    assert call_kwargs["reconciliation_status"] == "unmatched"