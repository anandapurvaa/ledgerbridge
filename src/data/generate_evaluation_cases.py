# src/data/generate_evaluation_cases.py
import json
import random
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any

RANDOM_SEED = 42
OUTPUT_PATH = Path("data/evaluation/heldout_reconciliation_cases.json")

VENDORS = [
    "Acme Cloud Services",
    "Globex Analytics",
    "Initech Software GmbH",
    "Umbrella Logistics",
    "Stark Industrial Supply",
    "Wayne Enterprise Systems",
    "Cyberdyne Data Solutions",
    "Massive Dynamic Research",
]

CURRENCIES = ["EUR", "USD", "GBP"]


def random_date(start: date, end: date) -> str:
    days = (end - start).days
    return (start + timedelta(days=random.randint(0, days))).isoformat()


def make_ledger_record(index: int) -> dict[str, Any]:
    vendor = random.choice(VENDORS)
    currency = random.choice(CURRENCIES)
    quantity = random.randint(1, 25)
    unit_price = round(random.uniform(25.0, 450.0), 2)

    # Keep EUR at 1.0. Other rates are synthetic rates to EUR.
    fx_rate = (
        1.0
        if currency == "EUR"
        else round(random.uniform(0.80, 1.25), 4)
    )

    amount = round(quantity * unit_price * fx_rate, 2)

    return {
        "invoice_id": f"EVAL-INV-{index:05d}",
        "invoice_date": random_date(
            start=date(2026, 1, 1),
            end=date(2026, 6, 30),
        ),
        "vendor": vendor,
        "amount": amount,
        "currency": currency,
        "quantity": quantity,
        "fx_rate": fx_rate,
        "line_items": json.dumps(
            [
                {
                    "description": "Professional services",
                    "quantity": quantity,
                    "unit_price": unit_price,
                }
            ]
        ),
    }


def make_case(
    case_id: str,
    scenario: str,
    ledger_record: dict[str, Any],
) -> dict[str, Any]:
    invoice = deepcopy(ledger_record)

    if scenario == "matched":
        pass

    elif scenario == "fx_mismatch":
        original_rate = float(invoice["fx_rate"])
        changed_rate = round(original_rate * 1.08, 4)

        # Ensure an actual change even if the rounding happens to preserve value.
        if changed_rate == original_rate:
            changed_rate = round(original_rate + 0.08, 4)

        invoice["fx_rate"] = changed_rate
        invoice["amount"] = round(
            float(invoice["amount"]) * (changed_rate / original_rate),
            2,
        )

    elif scenario == "quantity_mismatch":
        original_quantity = int(invoice["quantity"])
        new_quantity = original_quantity + 2

        invoice["quantity"] = new_quantity
        invoice["amount"] = round(
            float(invoice["amount"]) * (new_quantity / original_quantity),
            2,
        )

    elif scenario == "amount_mismatch":
        invoice["amount"] = round(float(invoice["amount"]) + 47.25, 2)

    elif scenario == "duplicate_charge":
        # Same invoice appears as an additional invoice submission.
        # We use an evaluation-only expected label; duplicate handling
        # will be implemented as a dedicated rule after this baseline.
        invoice["amount"] = float(invoice["amount"])

    else:
        raise ValueError(f"Unsupported scenario: {scenario}")

    return {
        "case_id": case_id,
        "expected_status": scenario,
        "invoice": invoice,
        "ledger_record": ledger_record,
    }


def generate_cases(
    records_per_scenario: int = 30,
    seed: int = RANDOM_SEED,
) -> list[dict[str, Any]]:
    random.seed(seed)

    scenarios = [
        "matched",
        "fx_mismatch",
        "quantity_mismatch",
        "amount_mismatch",
        "duplicate_charge",
    ]

    cases: list[dict[str, Any]] = []
    record_index = 1

    for scenario in scenarios:
        for scenario_index in range(records_per_scenario):
            ledger_record = make_ledger_record(record_index)

            cases.append(
                make_case(
                    case_id=f"{scenario}-{scenario_index + 1:03d}",
                    scenario=scenario,
                    ledger_record=ledger_record,
                )
            )

            record_index += 1

    return cases


def save_cases(cases: list[dict[str, Any]]) -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(cases, file, indent=2)

    return OUTPUT_PATH


def main():
    cases = generate_cases()
    output_path = save_cases(cases)

    scenario_counts: dict[str, int] = {}

    for case in cases:
        status = case["expected_status"]
        scenario_counts[status] = scenario_counts.get(status, 0) + 1

    print(f"Generated {len(cases)} held-out evaluation cases.")
    print(f"Saved to: {output_path}")
    print("Scenario distribution:")

    for scenario, count in scenario_counts.items():
        print(f"  {scenario}: {count}")


if __name__ == "__main__":
    main()