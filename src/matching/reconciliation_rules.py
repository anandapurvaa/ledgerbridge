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


def has_same_identity(
    invoice: InvoiceRecord,
    ledger: InvoiceRecord,
) -> bool:
    """
    Invoice ID is the strongest identity signal.
    If it is unavailable or differs, use vendor + date as a weaker fallback.
    """
    if invoice.invoice_id and invoice.invoice_id == ledger.invoice_id:
        return True

    return (
        invoice.vendor.strip().lower() == ledger.vendor.strip().lower()
        and invoice.invoice_date == ledger.invoice_date
    )


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
    ledger = best.ledger_record

    # 1. Candidate retrieval confidence comes first.
    if best.semantic_score < SEMANTIC_MATCH_THRESHOLD:
        return ReconciliationResult(
            status="unmatched",
            confidence=round(1 - max(best.semantic_score, 0), 4),
            best_match=ledger,
            candidate_matches=candidates,
            discrepancy_details={
                "reason": "Highest semantic similarity is below the match threshold.",
                "best_semantic_score": best.semantic_score,
            },
        )

    # 2. A verified invoice identity is stronger than FAISS score ambiguity.
    # This allows exact known invoices and known discrepancy scenarios
    # to proceed to deterministic financial validation.
    if not has_same_identity(invoice, ledger):
        if len(candidates) > 1:
            second = candidates[1]
            score_gap = best.semantic_score - second.semantic_score

            if score_gap < AMBIGUITY_MARGIN:
                return ReconciliationResult(
                    status="ambiguous",
                    confidence=round(best.semantic_score, 4),
                    best_match=ledger,
                    candidate_matches=candidates,
                    discrepancy_details={
                        "reason": (
                            "No stable invoice identity was verified and the "
                            "top two semantic candidates are too similar."
                        ),
                        "best_score": best.semantic_score,
                        "second_score": second.semantic_score,
                        "score_gap": round(score_gap, 4),
                    },
                )

        return ReconciliationResult(
            status="unmatched",
            confidence=round(1 - best.semantic_score, 4),
            best_match=ledger,
            candidate_matches=candidates,
            discrepancy_details={
                "reason": (
                    "Top candidate does not share an invoice ID or a "
                    "vendor-and-date identity with the input invoice."
                ),
                "input_invoice_id": invoice.invoice_id,
                "candidate_invoice_id": ledger.invoice_id,
                "input_vendor": invoice.vendor,
                "candidate_vendor": ledger.vendor,
            },
        )

    # 3. Once identity is confirmed, run financial controls.
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

    # 4. Identity and all financial checks agree.
    return ReconciliationResult(
        status="matched",
        confidence=round(best.semantic_score, 4),
        best_match=ledger,
        candidate_matches=candidates,
        discrepancy_details={
            "reason": (
                "Identity, currency, quantity, FX rate, and amount agree "
                "within configured tolerances."
            ),
        },
    )