# tests/matching/test_embedding_matcher.py
from src.matching.embedding_matcher import LedgerEmbeddingMatcher
from src.matching.reconciliation_rules import classify_reconciliation
from src.matching.schemas import InvoiceRecord


LEDGER_ROWS = [
    {
        "invoice_id": "INV-00001",
        "invoice_date": "2026-01-10",
        "vendor": "Acme Corp",
        "amount": 1200.00,
        "currency": "EUR",
        "quantity": 10,
        "fx_rate": 1.0000,
        "line_items": '[{"desc": "Cloud infrastructure support", "qty": 10, "price": 120.0}]',
    },
    {
        "invoice_id": "INV-00002",
        "invoice_date": "2026-01-11",
        "vendor": "Globex Inc",
        "amount": 550.00,
        "currency": "EUR",
        "quantity": 5,
        "fx_rate": 1.0000,
        "line_items": '[{"desc": "Data integration consulting", "qty": 5, "price": 110.0}]',
    },
    {
        "invoice_id": "INV-00003",
        "invoice_date": "2026-01-12",
        "vendor": "Initech",
        "amount": 900.00,
        "currency": "USD",
        "quantity": 9,
        "fx_rate": 1.0800,
        "line_items": '[{"desc": "Software licenses", "qty": 9, "price": 100.0}]',
    },
]


def create_matcher() -> LedgerEmbeddingMatcher:
    matcher = LedgerEmbeddingMatcher()
    matcher.build_index(LEDGER_ROWS)
    return matcher


def test_exact_invoice_is_matched():
    invoice = InvoiceRecord(
        invoice_id="INV-00001",
        invoice_date="2026-01-10",
        vendor="Acme Corp",
        amount=1200.00,
        currency="EUR",
        quantity=10,
        fx_rate=1.0000,
        line_items='[{"desc": "Cloud infrastructure support"}]',
    )

    result = classify_reconciliation(
        invoice,
        create_matcher().search(invoice, top_k=3),
    )

    assert result.status == "matched"
    assert result.best_match is not None
    assert result.best_match.invoice_id == "INV-00001"


def test_quantity_difference_is_flagged():
    invoice = InvoiceRecord(
        invoice_id="INV-00001",
        invoice_date="2026-01-10",
        vendor="Acme Corp",
        amount=1320.00,
        currency="EUR",
        quantity=11,
        fx_rate=1.0000,
        line_items='[{"desc": "Cloud infrastructure support"}]',
    )

    result = classify_reconciliation(
        invoice,
        create_matcher().search(invoice, top_k=3),
    )

    assert result.status == "quantity_mismatch"
    assert result.discrepancy_details["quantity_delta"] == 1


def test_fx_difference_is_flagged():
    invoice = InvoiceRecord(
        invoice_id="INV-00003",
        invoice_date="2026-01-12",
        vendor="Initech",
        amount=1000.00,
        currency="USD",
        quantity=9,
        fx_rate=1.2000,
        line_items='[{"desc": "Software licenses"}]',
    )

    result = classify_reconciliation(
        invoice,
        create_matcher().search(invoice, top_k=3),
    )

    assert result.status == "fx_mismatch"