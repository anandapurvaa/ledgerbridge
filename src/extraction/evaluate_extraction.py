# src/extraction/evaluate_extraction.py
from collections import Counter

from datasets import load_dataset

from src.extraction.sroie_preprocessor import (
    ID_TO_LABEL,
    preprocess_sroie_sample,
)

DATASET_NAME = "jsdnrs/ICDAR2019-SROIE"


def main() -> None:
    dataset = load_dataset(DATASET_NAME)

    for split_name, split in dataset.items():
        label_counts = Counter()
        documents_with_label = Counter()

        for sample in split:
            processed = preprocess_sroie_sample(sample)
            label_names = processed["label_names"]

            present_entity_types = set()

            for label_name in label_names:
                label_counts[label_name] += 1

                if label_name != "O":
                    entity_type = label_name.split("-", maxsplit=1)[1]
                    present_entity_types.add(entity_type)

            for entity_type in present_entity_types:
                documents_with_label[entity_type] += 1

        print(f"\nSplit: {split_name}")
        print(f"Documents: {len(split)}")

        print("\nToken label distribution:")
        for label_name, count in sorted(label_counts.items()):
            print(f"  {label_name:<10} {count}")

        print("\nDocument-level entity coverage:")
        for entity_type in ("VENDOR", "DATE", "TOTAL"):
            coverage = (
                documents_with_label[entity_type] / len(split)
            )

            print(
                f"  {entity_type:<10} "
                f"{documents_with_label[entity_type]}/{len(split)} "
                f"({coverage:.1%})"
            )


if __name__ == "__main__":
    main()