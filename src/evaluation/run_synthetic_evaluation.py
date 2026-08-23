# src/evaluation/run_synthetic_evaluation.py
from __future__ import annotations

import json
from pathlib import Path

from src.evaluation.evaluate_ocr_extraction import (
    evaluate_ocr_extraction,
)
from src.evaluation.evaluate_reconciliation_cases import (
    evaluate_reconciliation_cases,
)


MANIFEST_PATH = Path(
    "data/synthetic/manifest/"
    "invoice_image_manifest.json"
)

OUTPUT_PATH = Path(
    "artifacts/evaluation/"
    "synthetic_end_to_end_baseline_report.json"
)


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest missing: {MANIFEST_PATH}. "
            "Run the synthetic invoice generator first."
        )

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    print("Running OCR heuristic extraction evaluation...")
    ocr_report = evaluate_ocr_extraction(manifest)

    print("Running reconciliation rule evaluation...")
    reconciliation_report = evaluate_reconciliation_cases(
        manifest
    )

    combined_report = {
        "ocr_extraction": ocr_report,
        "reconciliation_rules": reconciliation_report,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            combined_report,
            file,
            indent=2,
        )

    print("\nSynthetic evaluation summary")
    print("-" * 50)

    print(
        "OCR all-fields exact accuracy: "
        f"{ocr_report['summary']['all_fields_exact_accuracy']:.2%}"
    )

    print(
        "Reconciliation-rule accuracy: "
        f"{reconciliation_report['summary']['accuracy']:.2%}"
    )

    print(f"\nReport saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()