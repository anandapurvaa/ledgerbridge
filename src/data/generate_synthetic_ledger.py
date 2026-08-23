# src/data/generate_synthetic_ledger.py
import json
import random
from datetime import date, timedelta
from google.cloud import bigquery

client = bigquery.Client()
PROJECT_ID = client.project
DATASET_ID = "ledgerbridge"
TABLE_ID = "invoices"

VENDORS = [
    "Acme Corp",
    "Globex Inc",
    "Initech",
    "Umbrella Corp",
    "Stark Industries",
    "Wayne Enterprises",
    "Cyberdyne Systems",
    "Massive Dynamic",
    "Hooli",
    "Soylent Corp"
]

CURRENCIES = ["EUR", "USD", "GBP", "PLN"]

def random_date(start=date(2025, 1, 1), end=date(2026, 8, 23)):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def generate_line_items(quantity, unit_price):
    return [
        {
            "desc": "Item A",
            "qty": quantity,
            "price": round(unit_price, 2)
        }
    ]

def generate_invoices(n=300):
    invoices = []
    for i in range(1, n + 1):
        vendor = random.choice(VENDORS)
        currency = random.choice(CURRENCIES)
        quantity = random.randint(1, 50)
        unit_price = round(random.uniform(10, 500), 2)
        fx_rate = round(random.uniform(0.85, 1.2), 4)
        amount = round(quantity * unit_price * fx_rate, 2)

        line_items = generate_line_items(quantity, unit_price)

        invoice = {
            "invoice_id": f"INV-{i:05d}",
            "invoice_date": random_date(),
            "vendor": vendor,
            "amount": amount,
            "currency": currency,
            "quantity": quantity,
            "fx_rate": fx_rate,
            "line_items": json.dumps(line_items),
            "_unit_price": unit_price,  # keep for discrepancy logic, not inserted
        }
        invoices.append(invoice)
    return invoices

def inject_discrepancies(invoices):
    """
    Inject some controlled discrepancies:
    - Duplicate charges (same invoice_id)
    - FX mismatches
    - Quantity errors
    """
    modified = list(invoices)

    # Duplicate some invoices (same ID, slightly different amount)
    for _ in range(20):
        orig = random.choice(invoices)
        dup = orig.copy()
        dup["invoice_id"] = orig["invoice_id"]
        dup["amount"] = round(orig["amount"] * random.uniform(0.9, 1.1), 2)
        modified.append(dup)

    # FX mismatches
    for _ in range(15):
        orig = random.choice(invoices)
        fx_err = orig.copy()
        fx_err["fx_rate"] = round(orig["fx_rate"] * random.uniform(0.9, 1.1), 4)
        # Recompute amount using quantity, unit_price, and new fx_rate
        unit_price = orig["_unit_price"]
        fx_err["amount"] = round(orig["quantity"] * unit_price * fx_err["fx_rate"], 2)
        modified.append(fx_err)

    # Quantity errors
    for _ in range(15):
        orig = random.choice(invoices)
        qty_err = orig.copy()
        qty_err["quantity"] = orig["quantity"] + random.choice([-1, 1, 2])
        qty_err["amount"] = round(qty_err["quantity"] * orig["_unit_price"] * orig["fx_rate"], 2)
        modified.append(qty_err)

    return modified

def load_to_bigquery(invoices):
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    rows_to_insert = []
    for inv in invoices:
        rows_to_insert.append(
            {
                "invoice_id": inv["invoice_id"],
                "invoice_date": inv["invoice_date"].isoformat() if isinstance(inv["invoice_date"], date) else inv["invoice_date"],
                "vendor": inv["vendor"],
                "amount": inv["amount"],
                "currency": inv["currency"],
                "quantity": inv["quantity"],
                "fx_rate": inv["fx_rate"],
                "line_items": inv["line_items"],
            }
        )

    errors = client.insert_rows_json(table_ref, rows_to_insert)

    if errors:
        print("Errors during insert:", errors)
    else:
        print(f"Inserted {len(rows_to_insert)} invoices into {table_ref}")

def main():
    invoices = generate_invoices(300)
    invoices = inject_discrepancies(invoices)
    load_to_bigquery(invoices)

if __name__ == "__main__":
    main()