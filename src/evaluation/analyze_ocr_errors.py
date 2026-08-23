# src/evaluation/analyze_ocr_errors.py
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


INPUT_PATH = Path(
    "artifacts/evaluation/"
    "synthetic_end_to_end_baseline_report.json"
)

OUTPUT_PATH = Path(
    "artifacts/evaluation/"
    "ocr_error_analysis.json"
)


def load_ocr_case_results() -> list[dict[str, Any]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation report not found: {INPUT_PATH}. "
            "Run `python -m src.evaluation.run_synthetic_evaluation` first."
        )

    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        report = json.load(file)

    return report["ocr_extraction"]["case_results"]


def summarize_errors(
    case_results: list[dict[str, Any]],
) -> dict[str, Any]:
    field_failures: Counter[str] = Counter()
    scenario_failures: dict[str, Counter[str]] = defaultdict(
        Counter
    )

    failed_cases: list[dict[str, Any]] = []

    for result in case_results:
        incorrect_fields = [
            field_name
            for field_name, is_correct in result[
                "field_correct"
            ].items()
            if not is_correct
        ]

        if not incorrect_fields:
            continue

        scenario = result["scenario"]

        for field_name in incorrect_fields:
            field_failures[field_name] += 1
            scenario_failures[scenario][field_name] += 1

        failed_cases.append(
            {
                "case_id": result["case_id"],
                "scenario": scenario,
                "image_path": result["image_path"],
                "incorrect_fields": incorrect_fields,
                "ground_truth": result["ground_truth"],
                "predicted": result["predicted"],
                "ocr_mean_confidence": result[
                    "ocr_mean_confidence"
                ],
            }
        )

    total_cases = len(case_results)
    failed_case_count = len(failed_cases)

    return {
        "summary": {
            "total_cases": total_cases,
            "failed_cases": failed_case_count,
            "fully_correct_cases": total_cases - failed_case_count,
            "all_fields_exact_accuracy": round(
                (total_cases - failed_case_count)
                / total_cases,
                4,
            )
            if total_cases
            else 0.0,
            "field_failure_counts": dict(field_failures),
            "field_failure_rates": {
                field_name: round(
                    count / total_cases,
                    4,
                )
                for field_name, count in field_failures.items()
            },
            "scenario_field_failure_counts": {
                scenario: dict(counts)
                for scenario, counts in scenario_failures.items()
            },
        },
        "failed_cases": failed_cases,
    }


def print_summary(
    analysis: dict[str, Any],
) -> None:
    summary = analysis["summary"]

    print("\nOCR Error Analysis")
    print("-" * 50)
    print(f"Total cases:         {summary['total_cases']}")
    print(f"Fully correct cases: {summary['fully_correct_cases']}")
    print(f"Failed cases:        {summary['failed_cases']}")
    print(
        "All-fields accuracy: "
        f"{summary['all_fields_exact_accuracy']:.2%}"
    )

    print("\nField failures:")

    failure_counts = summary["field_failure_counts"]
    failure_rates = summary["field_failure_rates"]

    for field_name, count in sorted(
        failure_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(
            f"  {field_name:<15} "
            f"{count:>3} failures "
            f"({failure_rates[field_name]:.2%})"
        )

    print("\nFailures by scenario:")

    for scenario, counts in sorted(
        summary[
            "scenario_field_failure_counts"
        ].items()
    ):
        rendered = ", ".join(
            f"{field}: {count}"
            for field, count in sorted(
                counts.items()
            )
        )

        print(f"  {scenario:<20} {rendered}")


def main() -> None:
    case_results = load_ocr_case_results()
    analysis = summarize_errors(case_results)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            analysis,
            file,
            indent=2,
        )

    print_summary(analysis)

    print(f"\nSaved analysis: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()