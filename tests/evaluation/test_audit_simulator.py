# tests/evaluation/test_audit_simulator.py
from src.evaluation.audit_simulator import (
    InMemoryAuditSimulator,
)


def test_first_match_is_accepted_then_second_is_duplicate():
    audit = InMemoryAuditSimulator()

    first = audit.evaluate_duplicate_status(
        invoice_id="LB-INV-00001",
        reconciliation_status="matched",
    )

    second = audit.evaluate_duplicate_status(
        invoice_id="LB-INV-00001",
        reconciliation_status="matched",
    )

    assert first == "matched"
    assert second == "duplicate_charge"


def test_mismatch_is_never_recorded_as_successful_match():
    audit = InMemoryAuditSimulator()

    status = audit.evaluate_duplicate_status(
        invoice_id="LB-INV-00002",
        reconciliation_status="amount_mismatch",
    )

    assert status == "amount_mismatch"

    later_match = audit.evaluate_duplicate_status(
        invoice_id="LB-INV-00002",
        reconciliation_status="matched",
    )

    assert later_match == "matched"