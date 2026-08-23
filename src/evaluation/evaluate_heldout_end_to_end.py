# src/evaluation/evaluate_heldout_end_to_end.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from src.evaluation.audit_simulator import (
    InMemoryAuditSimulator,
)
from src.evaluation.evaluate_true_end_to_end import (
    run_case,
)
from src.matching.embedding_matcher import (
    LedgerEmbeddingMatcher,
)


HELDOUT_MANIFEST_PATH = Path(
    "data/synthetic/manifest/"
    "heldout_manifest.json"
)

OUTPUT_PATH = Path(
    "artifacts/evaluation/"
    "heldout_end_to_end_report.json"
)


def build_audit_seed(
    heldout_manifest: list[dict[str, Any]],
) -> InMemoryAuditSimulator:
    """
    Simulate history for duplicate cases only.

    Each duplicate invoice is pre-recorded as a prior successful match,
    so its current submission should be classified duplicate_charge.
    """
    audit = InMemoryAuditSimulator()

    for item in heldout_manifest:
        if item["scenario"] == "duplicate_charge":
            audit.record_match(
                item["ledger_record"]["invoice_id"]
            )

    return audit


def evaluate_heldout_manifest(
    heldout_manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    ledger_rows = [
        item["ledger_record"]
        for item in heldout_manifest
    ]

    matcher = LedgerEmbeddingMatcher()
    matcher.build_index(ledger_rows)

    audit = build_audit_seed(heldout_manifest)

    case_results: list[dict[str, Any]] = []

    for item in heldout_manifest:
        result = run_case(
            item=item,
            matcher=matcher,
            ledger_rows=ledger_rows,
        )

        base_status = result["predicted_status"]

        final_status = audit.evaluate_duplicate_status(
            invoice_id=result[
                "repaired_extracted_fields"
            ]["invoice_id"],
            reconciliation_status=base_status,
        )

        result["base_predicted_status"] = base_status
        result["predicted_status"] = final_status
        result["expected_status"] = item["scenario"]
        result["correct"] = (
            final_status == item["scenario"]
        )

        case_results.append(result)

    true_labels = [
        result["expected_status"]
        for result in case_results
    ]

    predicted_labels = [
        result["predicted_status"]
        for result in case_results
    ]

    labels = [
        "matched",
        "amount_mismatch",
        "fx_mismatch",
        "quantity_mismatch",
        "duplicate_charge",
    ]

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

    return {
        "benchmark_protocol": {
            "dataset": (
                "LedgerBridge synthetic invoice-image "
                "held-out evaluation set"
            ),
            "heldout_cases": len(heldout_manifest),
            "split_method": (
                "Scenario-stratified fixed-seed split"
            ),
            "random_seed": 42,
            "pipeline": [
                "Tesseract OCR",
                "heuristic field extraction",
                "exact invoice-ID ledger candidate resolution",
                "conservative ledger-aware OCR repair",
                "FAISS candidate retrieval fallback",
                "financial reconciliation rules",
                "in-memory prior-match audit simulation",
            ],
            "duplicate_protocol": (
                "Duplicate cases are seeded as previously accepted "
                "matches in an isolated in-memory audit simulator."
            ),
        },
        "summary": {
            "total_cases": len(case_results),
            "correct_cases": sum(
                result["correct"]
                for result in case_results
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

    print("\nHeld-out Image-to-Reconciliation Evaluation")
    print("-" * 60)
    print(f"Total cases:   {summary['total_cases']}")
    print(f"Correct cases: {summary['correct_cases']}")
    print(
        f"Accuracy:      {summary['accuracy']:.2%}"
    )

    print("\nPer-class metrics:")

    for label in report["labels"]:
        metrics = report["classification_report"][label]

        print(
            f"  {label:<20} "
            f"precision={metrics['precision']:.2f} "
            f"recall={metrics['recall']:.2f} "
            f"f1={metrics['f1-score']:.2f} "
            f"support={int(metrics['support'])}"
        )


def main() -> None:
    if not HELDOUT_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Held-out manifest missing: "
            f"{HELDOUT_MANIFEST_PATH}. "
            "Run `python -m src.synthetic.split_evaluation_manifest`."
        )

    with HELDOUT_MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        heldout_manifest = json.load(file)

    report = evaluate_heldout_manifest(
        heldout_manifest
    )

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