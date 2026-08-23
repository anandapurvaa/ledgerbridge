# src/evaluation/evaluate_true_end_to_end.py
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from src.evaluation.evaluate_ocr_extraction import (
    normalize_text,
)
from src.extraction.heuristic_extractor import (
    extract_fields_from_ocr,
)
from src.extraction.ledger_aware_repair import (
    repair_extracted_fields,
)
from src.extraction.ocr_reader import read_ocr
from src.matching.embedding_matcher import (
    LedgerEmbeddingMatcher,
)
from src.matching.reconciliation_rules import (
    classify_reconciliation,
)
from src.matching.schemas import InvoiceRecord


MANIFEST_PATH = Path(
    "data/synthetic/manifest/"
    "invoice_image_manifest.json"
)

OUTPUT_PATH = Path(
    "artifacts/evaluation/"
    "true_end_to_end_reconciliation_report.json"
)

DUPLICATE_BASELINE_STATUS = "matched"


def baseline_expected_status(
    scenario: str,
) -> str:
    """
    Duplicate detection needs prior audit state. In this stateless
    image-to-reconciliation benchmark, an otherwise identical duplicate
    is indistinguishable from an initial legitimate submission.
    """
    if scenario == "duplicate_charge":
        return DUPLICATE_BASELINE_STATUS

    return scenario


def find_invoice_id_candidate(
    extracted_fields: dict[str, Any],
    ledger_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Narrow the candidate set using a high-confidence extracted invoice ID.

    Exact ID matching is intentionally deterministic; it is a stronger
    finance identity signal than embeddings.
    """
    extracted_invoice_id = normalize_text(
        extracted_fields.get("invoice_id", "")
    )

    if not extracted_invoice_id:
        return None

    for row in ledger_rows:
        if normalize_text(row["invoice_id"]) == extracted_invoice_id:
            return row

    return None

def prioritize_identity_candidate(
    ledger_candidate: dict[str, Any] | None,
    candidates: list,
) -> list:
    """
    Put a deterministic exact-invoice-ID candidate first.

    FAISS is still useful for ranking alternatives, but it must not
    override a verified invoice identity.
    """
    if ledger_candidate is None:
        return candidates

    identity_invoice_id = normalize_text(
        ledger_candidate["invoice_id"]
    )

    identity_candidate = None
    remaining_candidates = []

    for candidate in candidates:
        candidate_invoice_id = normalize_text(
            candidate.ledger_record.invoice_id
        )

        if candidate_invoice_id == identity_invoice_id:
            identity_candidate = candidate
        else:
            remaining_candidates.append(candidate)

    if identity_candidate is None:
        # This should be rare if top_k is large enough, but creates a
        # deterministic fallback candidate if FAISS did not return it.
        from src.matching.schemas import (
            InvoiceRecord,
            MatchCandidate,
        )

        identity_candidate = MatchCandidate(
            ledger_record=InvoiceRecord.model_validate(
                ledger_candidate
            ),
            semantic_score=1.0,
            rank=1,
        )

    return [
        identity_candidate,
        *remaining_candidates,
    ]

def run_case(
    item: dict[str, Any],
    matcher: LedgerEmbeddingMatcher,
    ledger_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    ocr_result = read_ocr(item["image_path"])

    original_extracted = extract_fields_from_ocr(
        ocr_result
    )

    ledger_candidate = find_invoice_id_candidate(
        extracted_fields=original_extracted,
        ledger_rows=ledger_rows,
    )

    repaired_extracted = repair_extracted_fields(
        extracted_fields=original_extracted,
        ledger_candidate=ledger_candidate,
    )

    invoice = InvoiceRecord.model_validate(
        repaired_extracted
    )

    candidates = matcher.search(
        invoice=invoice,
        top_k=5,
    )

    candidates = prioritize_identity_candidate(
        ledger_candidate=ledger_candidate,
        candidates=candidates,
    )

    reconciliation_result = classify_reconciliation(
        invoice=invoice,
        candidates=candidates,
    )

    expected_status = baseline_expected_status(
        item["scenario"]
    )

    predicted_status = reconciliation_result.status

    return {
        "case_id": item["case_id"],
        "scenario": item["scenario"],
        "baseline_expected_status": expected_status,
        "predicted_status": predicted_status,
        "correct": predicted_status == expected_status,
        "confidence": reconciliation_result.confidence,
        "original_extracted_fields": original_extracted,
        "repaired_extracted_fields": repaired_extracted,
        "ledger_identity_candidate": ledger_candidate,
        "repair_log": repaired_extracted[
            "extraction_metadata"
        ].get("ledger_aware_repairs", []),
        "reconciliation_details": (
            reconciliation_result.discrepancy_details
        ),
        "best_match": (
            reconciliation_result.best_match.model_dump()
            if reconciliation_result.best_match
            else None
        ),
        "candidate_matches": [
            {
                "rank": candidate.rank,
                "semantic_score": candidate.semantic_score,
                "ledger_record": candidate.ledger_record.model_dump(),
            }
            for candidate in candidates
        ],
        "ocr_mean_confidence": ocr_result[
            "mean_confidence"
        ],
    }


def evaluate_manifest(
    manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    ledger_rows = [
        item["ledger_record"]
        for item in manifest
    ]

    matcher = LedgerEmbeddingMatcher()
    matcher.build_index(ledger_rows)

    case_results = [
        run_case(
            item=item,
            matcher=matcher,
            ledger_rows=ledger_rows,
        )
        for item in manifest
    ]

    true_labels = [
        result["baseline_expected_status"]
        for result in case_results
    ]

    predicted_labels = [
        result["predicted_status"]
        for result in case_results
    ]

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

    matrix = confusion_matrix(
        true_labels,
        predicted_labels,
        labels=labels,
    )

    correct_cases = sum(
        result["correct"]
        for result in case_results
    )

    return {
        "summary": {
            "total_cases": len(case_results),
            "correct_cases": correct_cases,
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
                "duplicate_charge is mapped to matched in this stateless "
                "benchmark. A later audit-history benchmark evaluates "
                "true duplicate detection."
            ),
        },
        "labels": labels,
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
        "case_results": case_results,
    }


def print_summary(
    report: dict[str, Any],
) -> None:
    summary = report["summary"]

    print("\nTrue Image-to-Reconciliation Evaluation")
    print("-" * 55)
    print(f"Total cases:   {summary['total_cases']}")
    print(f"Correct cases: {summary['correct_cases']}")
    print(
        f"Accuracy:      {summary['accuracy']:.2%}"
    )

    print("\nPer-class metrics:")

    for label in report["labels"]:
        metrics = report["classification_report"].get(
            label,
            {},
        )

        print(
            f"  {label:<20} "
            f"precision={metrics.get('precision', 0.0):.2f} "
            f"recall={metrics.get('recall', 0.0):.2f} "
            f"f1={metrics.get('f1-score', 0.0):.2f} "
            f"support={int(metrics.get('support', 0))}"
        )


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}. "
            "Run synthetic image generation first."
        )

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    report = evaluate_manifest(manifest)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
        )

    print_summary(report)

    print(f"\nSaved report: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()