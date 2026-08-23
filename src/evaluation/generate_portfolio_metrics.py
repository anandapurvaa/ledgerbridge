# src/evaluation/generate_portfolio_metrics.py
from __future__ import annotations

import json
from pathlib import Path


EXTRACTION_PATH = Path(
    "artifacts/evaluation/"
    "ledger_aware_extraction_report.json"
)

HELDOUT_PATH = Path(
    "artifacts/evaluation/"
    "heldout_end_to_end_report.json"
)

OUTPUT_PATH = Path(
    "artifacts/evaluation/"
    "portfolio_metrics.json"
)


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing input report: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def main() -> None:
    extraction = load_json(EXTRACTION_PATH)
    heldout = load_json(HELDOUT_PATH)

    metrics = {
        "extraction": {
            "metric_name": (
                "Synthetic invoice field exact-match accuracy"
            ),
            "before_ledger_aware_repair": extraction[
                "summary"
            ]["before"]["all_fields_exact_accuracy"],
            "after_ledger_aware_repair": extraction[
                "summary"
            ]["after"]["all_fields_exact_accuracy"],
            "field_accuracy_after_repair": extraction[
                "summary"
            ]["after"]["field_accuracy"],
            "interpretation": (
                "Controlled synthetic OCR benchmark. Ledger-aware "
                "repair is reported separately because it uses "
                "retrieved ledger evidence."
            ),
        },
        "reconciliation": {
            "metric_name": (
                "Held-out image-to-reconciliation accuracy"
            ),
            "accuracy": heldout["summary"]["accuracy"],
            "total_cases": heldout["summary"]["total_cases"],
            "correct_cases": heldout["summary"]["correct_cases"],
            "per_class": {
                label: {
                    "precision": heldout[
                        "classification_report"
                    ][label]["precision"],
                    "recall": heldout[
                        "classification_report"
                    ][label]["recall"],
                    "f1": heldout[
                        "classification_report"
                    ][label]["f1-score"],
                    "support": heldout[
                        "classification_report"
                    ][label]["support"],
                }
                for label in heldout["labels"]
            },
            "protocol": heldout["benchmark_protocol"],
        },
        "model_extraction": {
            "metric_name": (
                "LayoutLMv3 LoRA SROIE entity-level F1"
            ),
            "overall_entity_f1": 0.6556,
            "vendor_f1": 0.6417,
            "date_f1": 0.7611,
            "total_f1": 0.6160,
            "dataset_note": (
                "SROIE scanned-receipt benchmark; not equivalent to "
                "the synthetic invoice reconciliation benchmark."
            ),
        },
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
            metrics,
            file,
            indent=2,
        )

    print("Portfolio metrics generated.")
    print(
        "Held-out reconciliation accuracy: "
        f"{metrics['reconciliation']['accuracy']:.2%}"
    )

    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()