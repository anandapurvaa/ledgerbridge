# src/synthetic/split_evaluation_manifest.py
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


INPUT_PATH = Path(
    "data/synthetic/manifest/"
    "invoice_image_manifest.json"
)

DEV_OUTPUT_PATH = Path(
    "data/synthetic/manifest/"
    "development_manifest.json"
)

HELDOUT_OUTPUT_PATH = Path(
    "data/synthetic/manifest/"
    "heldout_manifest.json"
)

RANDOM_SEED = 42
HELDOUT_FRACTION = 0.30


def stratified_split(
    manifest: list[dict[str, Any]],
    heldout_fraction: float = HELDOUT_FRACTION,
    seed: int = RANDOM_SEED,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not 0 < heldout_fraction < 1:
        raise ValueError(
            "heldout_fraction must be strictly between 0 and 1."
        )

    rng = random.Random(seed)

    groups: dict[str, list[dict[str, Any]]] = {}

    for item in manifest:
        scenario = item["scenario"]
        groups.setdefault(scenario, []).append(item)

    development: list[dict[str, Any]] = []
    heldout: list[dict[str, Any]] = []

    for scenario, cases in groups.items():
        shuffled = list(cases)
        rng.shuffle(shuffled)

        heldout_count = max(
            1,
            round(len(shuffled) * heldout_fraction),
        )

        heldout.extend(shuffled[:heldout_count])
        development.extend(shuffled[heldout_count:])

    rng.shuffle(development)
    rng.shuffle(heldout)

    return development, heldout


def save_manifest(
    path: Path,
    manifest: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            indent=2,
        )


def print_distribution(
    label: str,
    manifest: list[dict[str, Any]],
) -> None:
    counts = Counter(
        item["scenario"]
        for item in manifest
    )

    print(f"\n{label}: {len(manifest)} cases")

    for scenario, count in sorted(counts.items()):
        print(f"  {scenario:<20} {count}")


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Missing manifest: {INPUT_PATH}. "
            "Generate synthetic invoice images first."
        )

    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    development, heldout = stratified_split(manifest)

    save_manifest(
        DEV_OUTPUT_PATH,
        development,
    )

    save_manifest(
        HELDOUT_OUTPUT_PATH,
        heldout,
    )

    print_distribution(
        "Development set",
        development,
    )

    print_distribution(
        "Held-out set",
        heldout,
    )

    print(f"\nSaved: {DEV_OUTPUT_PATH}")
    print(f"Saved: {HELDOUT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()