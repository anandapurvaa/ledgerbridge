# tests/evaluation/test_evaluate_heldout_end_to_end.py
from src.evaluation.evaluate_heldout_end_to_end import (
    build_audit_seed,
)


def test_duplicate_cases_are_preseeded_in_audit():
    heldout_manifest = [
        {
            "scenario": "duplicate_charge",
            "ledger_record": {
                "invoice_id": "LB-INV-00001",
            },
        },
        {
            "scenario": "matched",
            "ledger_record": {
                "invoice_id": "LB-INV-00002",
            },
        },
    ]

    audit = build_audit_seed(heldout_manifest)

    assert audit.has_prior_match("LB-INV-00001")
    assert not audit.has_prior_match("LB-INV-00002")