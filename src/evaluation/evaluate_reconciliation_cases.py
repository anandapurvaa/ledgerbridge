# src/evaluation/evaluate_reconciliation_cases.py
from __future__ import annotations

from copy import deepcopy
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    classification_report,
)

from src.matching.embedding_matcher import (
    LedgerEmbeddingMatcher,
)
from src.matching.reconciliation_rules import (
    classify_reconciliation,
)
from src.matching.schemas import InvoiceRecord


def evaluate_reconciliation_cases(
    manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Evaluate reconciliation logic against manifest ground truth.

    This uses manifest document fields—not OCR predictions—so it
    measures matching/rule correctness independently from extraction.
    """
    ledger_rows = [
        item["ledger_record"]
        for item in manifest
    ]

    matcher = LedgerEmbeddingMatcher()
    matcher.build_index(ledger_rows)

    true_labels: list[str] = []
    predicted_labels: list[str] = []
    case_results: list[dict[str, Any]] = []

    for item in manifest:
        invoice = InvoiceRecord.model_validate(
            item["document_invoice"]
        )

        candidates = matcher.search(
            invoice=invoice,
            top_k=5,
        )

        result = classify_reconciliation(
            invoice=invoice,
            candidates=candidates,
        )

        expected_status = item["scenario"]

        # Duplicate needs audit history, not only ledger matching.
        # Temporarily map it to matched for rule-engine-only evaluation.
        if expected_status == "duplicate_charge":
            baseline_expected_status = "matched"
        else:
            baseline_expected_status = expected_status

        true_labels.append(baseline_expected_status)
        predicted_labels.append(result.status)

        case_results.append(
            {
                "case_id": item["case_id"],
                "scenario": expected_status,
                "baseline_expected_status": baseline_expected_status,
                "predicted_status": result.status,
                "correct": (
                    result.status
                    == baseline_expected_status
                ),
                "confidence": result.confidence,
                "details": result.discrepancy_details,
                "best_match": (
                    result.best_match.model_dump()
                    if result.best_match
                    else None
                ),
            }
        )

    labels = sorted(
        set(true_labels) | set(predicted_labels)
    )

    report = classification_report(
        true_labels,
        predicted_labels,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )

    return {
        "summary": {
            "total_cases": len(manifest),
            "correct_cases": sum(
                case["correct"]
                for case in case_results
            ),
            "accuracy": round(
                float(
                    accuracy_score(
                        true_labels,
                        predicted_labels,
                    )
                ),
                4,
            ),
            "duplicate_charge_note": (
                "Duplicate charges are mapped to matched in this "
                "rule-engine evaluation. A separate audit-history "
                "evaluation measures true duplicate detection."
            ),
        },
        "classification_report": report,
        "case_results": case_results,
    }