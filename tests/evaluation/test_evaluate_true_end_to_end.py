# tests/evaluation/test_evaluate_true_end_to_end.py
from src.evaluation.evaluate_true_end_to_end import (
    baseline_expected_status,
    find_invoice_id_candidate,
)
from src.matching.schemas import (
    InvoiceRecord,
    MatchCandidate,
)
from src.evaluation.evaluate_true_end_to_end import (
    prioritize_identity_candidate,
)

def test_identity_candidate_is_moved_to_first_position():
    first_candidate = MatchCandidate(
        ledger_record=InvoiceRecord(
            invoice_id="LB-INV-00002",
            invoice_date="2026-08-23",
            vendor="Globex",
            amount=100.0,
            currency="EUR",
            quantity=1,
            fx_rate=1.0,
            line_items=[],
        ),
        semantic_score=0.95,
        rank=1,
    )

    identity_candidate = MatchCandidate(
        ledger_record=InvoiceRecord(
            invoice_id="LB-INV-00001",
            invoice_date="2026-08-23",
            vendor="Acme",
            amount=200.0,
            currency="EUR",
            quantity=2,
            fx_rate=1.0,
            line_items=[],
        ),
        semantic_score=0.90,
        rank=2,
    )

    result = prioritize_identity_candidate(
        ledger_candidate={
            "invoice_id": "LB-INV-00001",
            "invoice_date": "2026-08-23",
            "vendor": "Acme",
            "amount": 200.0,
            "currency": "EUR",
            "quantity": 2,
            "fx_rate": 1.0,
            "line_items": [],
        },
        candidates=[
            first_candidate,
            identity_candidate,
        ],
    )

    assert result[0].ledger_record.invoice_id == (
        "LB-INV-00001"
    )


def test_identity_candidate_is_created_when_missing_from_faiss():
    faiss_candidate = MatchCandidate(
        ledger_record=InvoiceRecord(
            invoice_id="LB-INV-00002",
            invoice_date="2026-08-23",
            vendor="Globex",
            amount=100.0,
            currency="EUR",
            quantity=1,
            fx_rate=1.0,
            line_items=[],
        ),
        semantic_score=0.95,
        rank=1,
    )

    result = prioritize_identity_candidate(
        ledger_candidate={
            "invoice_id": "LB-INV-00001",
            "invoice_date": "2026-08-23",
            "vendor": "Acme",
            "amount": 200.0,
            "currency": "EUR",
            "quantity": 2,
            "fx_rate": 1.0,
            "line_items": [],
        },
        candidates=[faiss_candidate],
    )

    assert result[0].ledger_record.invoice_id == (
        "LB-INV-00001"
    )

    assert result[0].semantic_score == 1.0
    
def test_duplicate_is_mapped_to_matched_in_stateless_baseline():
    assert baseline_expected_status(
        "duplicate_charge"
    ) == "matched"

    assert baseline_expected_status(
        "amount_mismatch"
    ) == "amount_mismatch"


def test_invoice_id_candidate_is_found_exactly():
    extracted_fields = {
        "invoice_id": "LB-INV-00001",
    }

    ledger_rows = [
        {
            "invoice_id": "LB-INV-00002",
            "vendor": "Globex",
        },
        {
            "invoice_id": "LB-INV-00001",
            "vendor": "Acme",
        },
    ]

    candidate = find_invoice_id_candidate(
        extracted_fields=extracted_fields,
        ledger_rows=ledger_rows,
    )

    assert candidate is not None
    assert candidate["vendor"] == "Acme"


def test_invoice_id_candidate_returns_none_when_unknown():
    candidate = find_invoice_id_candidate(
        extracted_fields={
            "invoice_id": "UNKNOWN-INVOICE-ID",
        },
        ledger_rows=[],
    )

    assert candidate is None