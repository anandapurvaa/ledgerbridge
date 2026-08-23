# src/evaluation/evaluate_ocr_extraction.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score

from PIL import Image

from src.extraction.heuristic_extractor import (
    extract_fields_from_ocr,
)
from src.extraction.ocr_reader import read_ocr


def normalize_text(value: str) -> str:
    return " ".join(
        str(value)
        .strip()
        .lower()
        .replace(",", "")
        .replace(".", "")
        .split()
    )


def evaluate_ocr_extraction(
    manifest: list[dict[str, Any]],
    max_cases: int | None = None,
) -> dict[str, Any]:
    """
    Evaluate extraction only. Matching is intentionally excluded here.

    This makes failures diagnosable:
      - Wrong invoice ID: extraction issue.
      - Right fields but wrong mismatch label: reconciliation issue.
    """
    cases = (
        manifest[:max_cases]
        if max_cases is not None
        else manifest
    )

    field_names = [
        "invoice_id",
        "invoice_date",
        "vendor",
        "amount",
        "currency",
        "quantity",
        "fx_rate",
    ]

    field_correct_counts = {
        field_name: 0
        for field_name in field_names
    }

    results: list[dict[str, Any]] = []

    for item in cases:
        ground_truth = item["document_invoice"]

        ocr_result = read_ocr(item["image_path"])

        predicted = extract_fields_from_ocr(ocr_result)

        extraction_result = {
            "extracted_fields": predicted,
            "ocr_result": ocr_result,
        }

        field_correct = {
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
                        "fx_rate": (
                abs(
                    float(predicted["fx_rate"])
                    - float(ground_truth["fx_rate"])
                )
                <= 0.0001
            ),
        }

        for field_name, is_correct in field_correct.items():
            if is_correct:
                field_correct_counts[field_name] += 1

        results.append(
            {
                "case_id": item["case_id"],
                "scenario": item["scenario"],
                "image_path": item["image_path"],
                "ground_truth": ground_truth,
                "predicted": predicted,
                "field_correct": field_correct,
                "ocr_mean_confidence": extraction_result[
                    "ocr_result"
                ]["mean_confidence"],
            }
        )

    total_cases = len(cases)

    field_accuracy = {
        field_name: round(
            count / total_cases,
            4,
        )
        if total_cases
        else 0.0
        for field_name, count in field_correct_counts.items()
    }

    all_fields_correct = sum(
        all(result["field_correct"].values())
        for result in results
    )

    return {
        "summary": {
            "total_cases": total_cases,
            "all_fields_exact_accuracy": round(
                all_fields_correct / total_cases,
                4,
            )
            if total_cases
            else 0.0,
            "field_accuracy": field_accuracy,
        },
        "case_results": results,
    }


def main() -> None:
    manifest_path = Path(
        "data/synthetic/manifest/"
        "invoice_image_manifest.json"
    )

    with manifest_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    report = evaluate_ocr_extraction(manifest)

    output_path = Path(
        "artifacts/evaluation/ocr_extraction_report.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
        )

    print("OCR extraction evaluation")
    print("-" * 40)

    for field_name, score in report["summary"][
        "field_accuracy"
    ].items():
        print(
            f"{field_name:<15} {score:.2%}"
        )

    print(
        "All fields exact: "
        f"{report['summary']['all_fields_exact_accuracy']:.2%}"
    )

    print(f"\nSaved report: {output_path}")


if __name__ == "__main__":
    main()