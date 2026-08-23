# src/extraction/diagnose_sroie_date_labels.py
from datasets import load_dataset

from src.extraction.sroie_preprocessor import (
    assign_bio_labels,
    parse_date_to_iso,
)

DATASET_NAME = "jsdnrs/ICDAR2019-SROIE"
MAX_EXAMPLES_PER_SPLIT = 15


def main() -> None:
    dataset = load_dataset(DATASET_NAME)

    for split_name, split in dataset.items():
        printed = 0
        missing = 0

        print(f"\nSplit: {split_name}")

        for sample in split:
            labels = assign_bio_labels(
                words=sample["words"],
                entities=sample["entities"],
            )

            has_date = any(
                label.endswith("DATE")
                for label in labels
            )

            if has_date:
                continue

            missing += 1

            if printed >= MAX_EXAMPLES_PER_SPLIT:
                continue

            ground_truth_date = sample["entities"].get(
                "date",
                "",
            )

            print("-" * 75)
            print(f"Key: {sample['key']}")
            print(
                "Ground truth raw date: "
                f"{ground_truth_date!r}"
            )
            print(
                "Ground truth parsed date: "
                f"{parse_date_to_iso(ground_truth_date)!r}"
            )
            print("OCR words containing digits:")

            digit_words = [
                word
                for word in sample["words"]
                if any(char.isdigit() for char in word)
            ]

            for word in digit_words[:30]:
                print(f"  {word!r}")

            printed += 1

        print(
            f"\nDate-label misses: {missing}/{len(split)} "
            f"({missing / len(split):.1%})"
        )


if __name__ == "__main__":
    main()