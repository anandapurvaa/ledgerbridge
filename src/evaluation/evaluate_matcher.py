# src/evaluation/evaluate_matcher.py
import json
from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score, classification_report

from src.matching.embedding_matcher import LedgerEmbeddingMatcher
from src.matching.reconciliation_rules import classify_reconciliation
from src.matching.schemas import InvoiceRecord

INPUT_PATH = Path("data/evaluation/heldout_reconciliation_cases.json")
OUTPUT_DIR = Path("artifacts/evaluation")
OUTPUT_PATH = OUTPUT_DIR / "matcher_evaluation_report.json"

# Honest baseline behavior: a duplicate is indistinguishable from a
# legitimate re-submitted invoice until audit history is implemented.
EXPECTED_TO_BASELINE_STATUS = {}


def load_cases() -> list[dict[str, Any]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation data does not exist: {INPUT_PATH}. "
            "Run `python -m src.data.generate_evaluation_cases` first."
        )

    with INPUT_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def baseline_expected_status(expected_status: str) -> str:
    return EXPECTED_TO_BASELINE_STATUS.get(
        expected_status,
        expected_status,
    )


def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    y_true: list[str] = []
    y_pred: list[str] = []
    per_case_results: list[dict[str, Any]] = []

    for case in cases:
        invoice = InvoiceRecord.model_validate(case["invoice"])

        # One ledger record per case isolates the financial-rule baseline.
        # In the next phase, we will evaluate retrieval against a larger index.
        matcher = LedgerEmbeddingMatcher()
        matcher.build_index([case["ledger_record"]])

        candidates = matcher.search(invoice, top_k=1)
        result = classify_reconciliation(invoice, candidates)

        expected_status = baseline_expected_status(
            case["expected_status"]
        )

        y_true.append(expected_status)
        y_pred.append(result.status)

        per_case_results.append(
            {
                "case_id": case["case_id"],
                "scenario": case["expected_status"],
                "baseline_expected_status": expected_status,
                "predicted_status": result.status,
                "correct": result.status == expected_status,
                "confidence": result.confidence,
                "semantic_score": candidates[0].semantic_score,
                "details": result.discrepancy_details,
            }
        )

    labels = sorted(set(y_true) | set(y_pred))

    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )

    accuracy = accuracy_score(y_true, y_pred)

    return {
        "summary": {
            "total_cases": len(cases),
            "correct_cases": sum(
                item["correct"] for item in per_case_results
            ),
            "accuracy": round(float(accuracy), 4),
            "duplicate_charge_note": (
                "Duplicate charges are mapped to matched in this baseline. "
                "Duplicate detection requires persisted audit history and "
                "will be measured separately after that capability exists."
            ),
        },
        "classification_report": report,
        "case_results": per_case_results,
    }


def save_report(report: dict[str, Any]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    return OUTPUT_PATH


def print_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]

    print("\nLedgerBridge Matcher Baseline Evaluation")
    print("-" * 45)
    print(f"Total cases:   {summary['total_cases']}")
    print(f"Correct cases: {summary['correct_cases']}")
    print(f"Accuracy:      {summary['accuracy']:.2%}")

    print("\nPer-class F1:")
    for label, metrics in report["classification_report"].items():
        if label in {"accuracy", "macro avg", "weighted avg"}:
            continue

        print(
            f"  {label:<20} "
            f"precision={metrics['precision']:.2f} "
            f"recall={metrics['recall']:.2f} "
            f"f1={metrics['f1-score']:.2f} "
            f"support={int(metrics['support'])}"
        )

    print(f"\nFull JSON report saved to: {OUTPUT_PATH}")


def main():
    cases = load_cases()
    report = evaluate_cases(cases)
    save_report(report)
    print_summary(report)


if __name__ == "__main__":
    main()