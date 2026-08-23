# src/evaluation/generate_evaluation_summary.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


INPUT_PATH = Path(
    "artifacts/evaluation/ocr_error_analysis.json"
)


def print_case(
    case: dict[str, Any],
) -> None:
    print("=" * 88)
    print(
        f"Case: {case['case_id']} "
        f"| Scenario: {case['scenario']}"
    )

    print(f"Image: {case['image_path']}")

    print(
        "OCR mean confidence: "
        f"{case['ocr_mean_confidence']}"
    )

    print(
        "Incorrect fields: "
        f"{', '.join(case['incorrect_fields'])}"
    )

    print("\nGround truth:")

    for key, value in case["ground_truth"].items():
        if key != "line_items":
            print(f"  {key:<15} {value}")

    print("\nPredicted:")

    for key, value in case["predicted"].items():
        if key not in {
            "line_items",
            "extraction_metadata",
        }:
            print(f"  {key:<15} {value}")


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Error analysis not found: {INPUT_PATH}. "
            "Run `python -m src.evaluation.analyze_ocr_errors` first."
        )

    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        analysis = json.load(file)

    failures = analysis["failed_cases"]

    print(f"Displaying {min(10, len(failures))} failures.")

    for case in failures[:10]:
        print_case(case)


if __name__ == "__main__":
    main()