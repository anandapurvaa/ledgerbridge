# src/synthetic/generate_invoice_image_dataset.py
from __future__ import annotations

import json
import random
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.synthetic.invoice_renderer import render_invoice


RANDOM_SEED = 42
IMAGE_DIR = Path("data/synthetic/invoice_images")
MANIFEST_PATH = Path(
    "data/synthetic/manifest/invoice_image_manifest.json"
)

VENDORS = [
    "Acme Cloud Services",
    "Globex Analytics GmbH",
    "Initech Software Solutions",
    "Umbrella Logistics Europe",
    "Stark Industrial Supply",
    "Wayne Enterprise Systems",
    "Cyberdyne Data Solutions",
    "Massive Dynamic Research",
]

CURRENCIES = ["EUR", "USD", "GBP", "PLN"]


def random_date(
    start: date = date(2026, 1, 1),
    end: date = date(2026, 8, 31),
) -> str:
    return (
        start
        + timedelta(
            days=random.randint(
                0,
                (end - start).days,
            )
        )
    ).isoformat()


def make_base_invoice(index: int) -> dict[str, Any]:
    vendor = random.choice(VENDORS)
    currency = random.choice(CURRENCIES)
    quantity = random.randint(1, 20)
    unit_price = round(
        random.uniform(35.0, 350.0),
        2,
    )

    fx_rate = (
        1.0
        if currency == "EUR"
        else round(random.uniform(0.85, 1.20), 4)
    )

    amount = round(
        quantity * unit_price * fx_rate,
        2,
    )

    return {
        "invoice_id": f"LB-INV-{index:05d}",
        "invoice_date": random_date(),
        "vendor": vendor,
        "amount": amount,
        "currency": currency,
        "quantity": quantity,
        "fx_rate": fx_rate,
        "line_items": [
            {
                "description": random.choice(
                    [
                        "Cloud platform support",
                        "Data engineering services",
                        "Software subscription",
                        "Infrastructure consulting",
                        "Analytics implementation",
                    ]
                ),
                "qty": quantity,
                "price": unit_price,
            }
        ],
    }


def make_document_variant(
    ledger_record: dict[str, Any],
    scenario: str,
) -> dict[str, Any]:
    """
    Produce the invoice-side fields rendered into the document image.
    The ledger record remains unchanged and is the reconciliation truth.
    """
    document = deepcopy(ledger_record)

    if scenario == "matched":
        return document

    if scenario == "amount_mismatch":
        document["amount"] = round(
            float(document["amount"]) + 37.50,
            2,
        )
        return document

    if scenario == "fx_mismatch":
        original_fx = float(document["fx_rate"])
        document["fx_rate"] = round(
            original_fx * 1.08,
            4,
        )
        document["amount"] = round(
            float(document["amount"])
            * document["fx_rate"]
            / original_fx,
            2,
        )
        return document

    if scenario == "quantity_mismatch":
        new_quantity = int(document["quantity"]) + 2
        old_quantity = int(document["quantity"])

        document["quantity"] = new_quantity
        document["amount"] = round(
            float(document["amount"])
            * new_quantity
            / old_quantity,
            2,
        )

        document["line_items"][0]["qty"] = new_quantity
        return document

    if scenario == "duplicate_charge":
        return document

    raise ValueError(
        f"Unsupported scenario: {scenario}"
    )


def build_dataset(
    records_per_scenario: int = 20,
    seed: int = RANDOM_SEED,
) -> list[dict[str, Any]]:
    random.seed(seed)

    scenarios = [
        "matched",
        "amount_mismatch",
        "fx_mismatch",
        "quantity_mismatch",
        "duplicate_charge",
    ]

    manifest: list[dict[str, Any]] = []
    record_index = 1

    for scenario in scenarios:
        for scenario_index in range(records_per_scenario):
            ledger_record = make_base_invoice(record_index)

            document_invoice = make_document_variant(
                ledger_record=ledger_record,
                scenario=scenario,
            )

            filename = (
                f"{scenario}_{record_index:05d}.png"
            )

            image_path = IMAGE_DIR / filename

            render_invoice(
                invoice=document_invoice,
                output_path=image_path,
                seed=seed + record_index,
            )

            manifest.append(
                {
                    "case_id": (
                        f"{scenario}-{scenario_index + 1:03d}"
                    ),
                    "scenario": scenario,
                    "image_path": str(image_path),
                    "document_invoice": document_invoice,
                    "ledger_record": ledger_record,
                }
            )

            record_index += 1

    return manifest


def save_manifest(
    manifest: list[dict[str, Any]],
) -> Path:
    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            indent=2,
        )

    return MANIFEST_PATH


def main() -> None:
    manifest = build_dataset()
    manifest_path = save_manifest(manifest)

    print(
        f"Generated {len(manifest)} invoice images."
    )

    print(f"Image directory: {IMAGE_DIR}")
    print(f"Manifest path: {manifest_path}")

    scenario_counts: dict[str, int] = {}

    for item in manifest:
        scenario = item["scenario"]
        scenario_counts[scenario] = (
            scenario_counts.get(scenario, 0) + 1
        )

    print("\nScenario counts:")

    for scenario, count in scenario_counts.items():
        print(f"  {scenario}: {count}")


if __name__ == "__main__":
    main()