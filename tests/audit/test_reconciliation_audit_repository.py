# tests/audit/test_reconciliation_audit_repository.py
from uuid import uuid4

from src.audit.reconciliation_audit_repository import (
    ReconciliationAuditRepository,
)
from src.matching.schemas import InvoiceRecord


def test_write_and_find_prior_matched_invoice():
    repository = ReconciliationAuditRepository()

    unique_invoice_id = f"TEST-AUDIT-{uuid4().hex[:12]}"

    invoice = InvoiceRecord(
        invoice_id=unique_invoice_id,
        invoice_date="2026-08-23",
        vendor="LedgerBridge Test Vendor",
        amount=123.45,
        currency="EUR",
        quantity=1,
        fx_rate=1.0,
        line_items="[]",
    )

    prior_event = repository.find_prior_successful_invoice(
        invoice
    )

    assert prior_event is None

    audit_event_id = repository.write_event(
        invoice=invoice,
        reconciliation_status="matched",
        run_id=f"pytest-{uuid4()}",
        source="pytest",
        matched_ledger_invoice_id=invoice.invoice_id,
        details={"test": True},
    )

    assert audit_event_id

    found_event = repository.find_prior_successful_invoice(
        invoice
    )

    assert found_event is not None
    assert found_event["audit_event_id"] == audit_event_id
    assert found_event["invoice_id"] == unique_invoice_id
    assert found_event["reconciliation_status"] == "matched"