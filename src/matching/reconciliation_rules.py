# src/matching/reconciliation_rules.py
from __future__ import annotations

from src.matching.schemas import (
    InvoiceRecord,
    MatchCandidate,
    ReconciliationResult,
)


AMOUNT_ABSOLUTE_TOLERANCE = 0.02
FX_RATE_TOLERANCE = 0.005
SEMANTIC_MATCH_THRESHOLD = 0.75
AMBIGUITY_MARGIN = 0.03


def relative_difference(expected: float, actual: float) -> float:
    if expected == 0:
        return 0.0 if actual == 0 else 1.0

    return abs(expected - actual) / abs(expected)


def classify_reconciliation(
    invoice: InvoiceRecord,
    candidates: list[MatchCandidate],
) -> ReconciliationResult:
    if not candidates:
        return ReconciliationResult(
            status="unmatched",
            confidence=1.0,
            discrepancy_details={
                "reason": "No candidate ledger records were retrieved.",
            },
        )

    best = candidates[0]

    if best.semantic_score < SEMANTIC_MATCH_THRESHOLD:
        return ReconciliationResult(
            status="unmatched",
            confidence=round(1 - max(best.semantic_score, 0), 4),
            best_match=best.ledger_record,
            candidate_matches=candidates,
            discrepancy_details={
                "reason": "Highest semantic similarity is below the match threshold.",
                "best_semantic_score": best.semantic_score,
            },
        )

    if len(candidates) > 1:
        score_gap = best.semantic_score - candidates[1].semantic_score

        if score_gap < AMBIGUITY_MARGIN:
            return ReconciliationResult(
                status="ambiguous",
                confidence=round(best.semantic_score, 4),
                best_match=best.ledger_record,
                candidate_matches=candidates,
                discrepancy_details={
                    "reason": "Two ledger candidates have near-identical similarity scores.",
                    "best_score": best.semantic_score,
                    "second_score": candidates[1].semantic_score,
                    "score_gap": round(score_gap, 4),
                },
            )

    ledger = best.ledger_record

    if invoice.currency != ledger.currency:
        return ReconciliationResult(
            status="currency_mismatch",
            confidence=round(best.semantic_score, 4),
            best_match=ledger,
            candidate_matches=candidates,
            discrepancy_details={
                "invoice_currency": invoice.currency,
                "ledger_currency": ledger.currency,
            },
        )

    if invoice.invoice_id == ledger.invoice_id:
        same_identity = True
    else:
        same_identity = (
            invoice.vendor.strip().lower() == ledger.vendor.strip().lower()
            and invoice.invoice_date == ledger.invoice_date
        )

    if not same_identity:
        return ReconciliationResult(
            status="unmatched",
            confidence=round(1 - best.semantic_score, 4),
            best_match=ledger,
            candidate_matches=candidates,
            discrepancy_details={
                "reason": "Candidate does not share the invoice ID or vendor-date identity.",
            },
        )

    if invoice.quantity != ledger.quantity:
        return ReconciliationResult(
            status="quantity_mismatch",
            confidence=round(best.semantic_score, 4),
            best_match=ledger,
            candidate_matches=candidates,
            discrepancy_details={
                "invoice_quantity": invoice.quantity,
                "ledger_quantity": ledger.quantity,
                "quantity_delta": invoice.quantity - ledger.quantity,
            },
        )

    fx_rate_delta = relative_difference(ledger.fx_rate, invoice.fx_rate)

    if fx_rate_delta > FX_RATE_TOLERANCE:
        return ReconciliationResult(
            status="fx_mismatch",
            confidence=round(best.semantic_score, 4),
            best_match=ledger,
            candidate_matches=candidates,
            discrepancy_details={
                "invoice_fx_rate": invoice.fx_rate,
                "ledger_fx_rate": ledger.fx_rate,
                "relative_fx_rate_difference": round(fx_rate_delta, 4),
            },
        )

    amount_delta = round(invoice.amount - ledger.amount, 2)

    if abs(amount_delta) > AMOUNT_ABSOLUTE_TOLERANCE:
        return ReconciliationResult(
            status="amount_mismatch",
            confidence=round(best.semantic_score, 4),
            best_match=ledger,
            candidate_matches=candidates,
            discrepancy_details={
                "invoice_amount": invoice.amount,
                "ledger_amount": ledger.amount,
                "amount_delta": amount_delta,
            },
        )

    return ReconciliationResult(
        status="matched",
        confidence=round(best.semantic_score, 4),
        best_match=ledger,
        candidate_matches=candidates,
        discrepancy_details={
            "reason": "Vendor/ID, currency, quantity, FX rate, and amount agree within configured tolerance.",
        },
    )