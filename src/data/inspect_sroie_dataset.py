# src/data/inspect_sroie_dataset.py
import json
from pathlib import Path
from typing import Any

from datasets import load_dataset


DATASET_NAME = "jsdnrs/ICDAR2019-SROIE"
OUTPUT_DIR = Path("data/raw/sroie_samples")
METADATA_PATH = OUTPUT_DIR / "dataset_inspection.json"


def to_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): to_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [to_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [to_json_safe(item) for item in value]

    return str(value)


def choose_split(dataset: Any) -> str:
    available_splits = list(dataset.keys())

    if "train" in available_splits:
        return "train"

    if not available_splits:
        raise RuntimeError("The loaded dataset has no splits.")

    return available_splits[0]


def main() -> None:
    print(f"Loading dataset: {DATASET_NAME}")

    dataset = load_dataset(DATASET_NAME)

    print("\nAvailable splits:")
    for split_name, split_data in dataset.items():
        print(f"  {split_name}: {len(split_data)} samples")

    split_name = choose_split(dataset)
    split = dataset[split_name]

    print(f"\nUsing split: {split_name}")
    print("Dataset features:")
    print(split.features)

    sample = split[0]

    print("\nFirst sample keys:")
    print(list(sample.keys()))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_key = None

    for key, value in sample.items():
        if hasattr(value, "save"):
            image_key = key
            value.save(OUTPUT_DIR / "sample_000.png")
            print(f"\nSaved image field '{key}' to:")
            print(OUTPUT_DIR / "sample_000.png")
            break

    sample_metadata = {
        key: to_json_safe(value)
        for key, value in sample.items()
        if key != image_key
    }

    inspection = {
        "dataset_name": DATASET_NAME,
        "selected_split": split_name,
        "split_size": len(split),
        "features": str(split.features),
        "sample_keys": list(sample.keys()),
        "image_key": image_key,
        "sample_metadata": sample_metadata,
    }

    with METADATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(inspection, file, indent=2)

    print(f"\nSaved metadata to: {METADATA_PATH}")

    print("\nSample metadata preview:")
    print(json.dumps(sample_metadata, indent=2)[:2500])


if __name__ == "__main__":
    main()