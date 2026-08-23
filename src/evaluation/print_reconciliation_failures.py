# src/evaluation/print_reconciliation_failures.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


INPUT_PATH = Path(
    "artifacts/evaluation/"
    "true_end_to_end_reconciliation_report.json"
)


def print_case(
    case: dict[str, Any],
) -> None:
    print("=" * 95)

    print(
        f"Case: {case['case_id']} | "
        f"Scenario: {case['scenario']}"
    )

    print(
        "Expected / predicted: "
        f"{case['baseline_expected_status']} / "
        f"{case['predicted_status']}"
    )

    print(f"Confidence: {case['confidence']}")
    print(
        "OCR mean confidence: "
        f"{case['ocr_mean_confidence']}"
    )

    print("\nOriginal extraction:")

    for key, value in case[
        "original_extracted_fields"
    ].items():
        if key not in {
            "line_items",
            "extraction_metadata",
        }:
            print(f"  {key:<15} {value}")

    print("\nRepaired extraction:")

    for key, value in case[
        "repaired_extracted_fields"
    ].items():
        if key not in {
            "line_items",
            "extraction_metadata",
        }:
            print(f"  {key:<15} {value}")

    print("\nRepairs:")

    if case["repair_log"]:
        for repair in case["repair_log"]:
            print(
                f"  {repair['field']}: "
                f"{repair['original_value']} → "
                f"{repair['repaired_value']}"
            )
    else:
        print("  None")

    print("\nRule details:")
    print(
        json.dumps(
            case["reconciliation_details"],
            indent=2,
        )
    )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Report missing: {INPUT_PATH}. "
            "Run `python -m src.evaluation.evaluate_true_end_to_end` "
            "first."
        )

    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        report = json.load(file)

    failures = [
        case
        for case in report["case_results"]
        if not case["correct"]
    ]

    print(
        f"Failures: {len(failures)} / "
        f"{report['summary']['total_cases']}"
    )

    for case in failures[:10]:
        print_case(case)


if __name__ == "__main__":
    main()