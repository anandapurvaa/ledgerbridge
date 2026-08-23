# src/evaluation/evaluate_ledger_aware_extraction.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


MANIFEST_PATH = Path(
    "data/synthetic/manifest/"
    "invoice_image_manifest.json"
)

OUTPUT_PATH = Path(
    "artifacts/evaluation/"
    "ledger_aware_extraction_report.json"
)


def compare_fields(
    predicted: dict[str, Any],
    ground_truth: dict[str, Any],
) -> dict[str, bool]:
    return {
        "invoice_id": (
            normalize_text(predicted["invoice_id"])
            == normalize_text(ground_truth["invoice_id"])
        ),
        "invoice_date": (
            predicted["invoice_date"]
            == ground_truth["invoice_date"]
        ),
        "vendor": (
            normalize_text(predicted["vendor"])
            == normalize_text(ground_truth["vendor"])
        ),
        "amount": (
            abs(
                float(predicted["amount"])
                - float(ground_truth["amount"])
            )
            <= 0.02
        ),
        "currency": (
            predicted["currency"]
            == ground_truth["currency"]
        ),
        "quantity": (
            int(predicted["quantity"])
            == int(ground_truth["quantity"])
        ),
    }


def evaluate(
    manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    field_names = [
        "invoice_id",
        "invoice_date",
        "vendor",
        "amount",
        "currency",
        "quantity",
    ]

    before_counts = {
        field_name: 0
        for field_name in field_names
    }

    after_counts = {
        field_name: 0
        for field_name in field_names
    }

    before_all_correct = 0
    after_all_correct = 0

    case_results: list[dict[str, Any]] = []

    for item in manifest:
        ocr_result = read_ocr(item["image_path"])

        extracted = extract_fields_from_ocr(
            ocr_result
        )

        repaired = repair_extracted_fields(
            extracted_fields=extracted,
            ledger_candidate=item["ledger_record"],
        )

        ground_truth = item["document_invoice"]

        before_correct = compare_fields(
            predicted=extracted,
            ground_truth=ground_truth,
        )

        after_correct = compare_fields(
            predicted=repaired,
            ground_truth=ground_truth,
        )

        for field_name in field_names:
            before_counts[field_name] += int(
                before_correct[field_name]
            )
            after_counts[field_name] += int(
                after_correct[field_name]
            )

        before_all_correct += int(
            all(before_correct.values())
        )

        after_all_correct += int(
            all(after_correct.values())
        )

        case_results.append(
            {
                "case_id": item["case_id"],
                "scenario": item["scenario"],
                "before_correct": before_correct,
                "after_correct": after_correct,
                "repairs": repaired[
                    "extraction_metadata"
                ]["ledger_aware_repairs"],
            }
        )

    total = len(manifest)

    return {
        "summary": {
            "total_cases": total,
            "before": {
                "all_fields_exact_accuracy": round(
                    before_all_correct / total,
                    4,
                ),
                "field_accuracy": {
                    field_name: round(
                        count / total,
                        4,
                    )
                    for field_name, count in before_counts.items()
                },
            },
            "after": {
                "all_fields_exact_accuracy": round(
                    after_all_correct / total,
                    4,
                ),
                "field_accuracy": {
                    field_name: round(
                        count / total,
                        4,
                    )
                    for field_name, count in after_counts.items()
                },
            },
        },
        "case_results": case_results,
    }


def main() -> None:
    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    report = evaluate(manifest)

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

    summary = report["summary"]

    print("\nLedger-aware extraction evaluation")
    print("-" * 50)

    print(
        "Before all-fields exact: "
        f"{summary['before']['all_fields_exact_accuracy']:.2%}"
    )

    print(
        "After all-fields exact:  "
        f"{summary['after']['all_fields_exact_accuracy']:.2%}"
    )

    print("\nField accuracy changes:")

    for field_name in summary["before"][
        "field_accuracy"
    ]:
        before = summary["before"][
            "field_accuracy"
        ][field_name]

        after = summary["after"][
            "field_accuracy"
        ][field_name]

        print(
            f"  {field_name:<15} "
            f"{before:.2%} → {after:.2%}"
        )

    print(f"\nSaved report: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()