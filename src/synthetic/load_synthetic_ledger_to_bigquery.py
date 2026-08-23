# src/synthetic/load_synthetic_ledger_to_bigquery.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.cloud import bigquery


MANIFEST_PATH = Path(
    "data/synthetic/manifest/invoice_image_manifest.json"
)

DATASET_ID = "ledgerbridge"
TABLE_ID = "synthetic_evaluation_ledger"


def load_manifest() -> list[dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}. "
            "Run `python -m src.synthetic.generate_invoice_image_dataset` first."
        )

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def create_table(
    client: bigquery.Client,
    project_id: str,
) -> str:
    dataset_ref = bigquery.DatasetReference(
        project_id,
        DATASET_ID,
    )

    client.create_dataset(
        dataset_ref,
        exists_ok=True,
    )

    table_ref = dataset_ref.table(TABLE_ID)

    schema = [
        bigquery.SchemaField(
            "case_id",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "scenario",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "invoice_id",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "invoice_date",
            "DATE",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "vendor",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "amount",
            "FLOAT64",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "currency",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "quantity",
            "INT64",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "fx_rate",
            "FLOAT64",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "line_items",
            "JSON",
            mode="NULLABLE",
        ),
    ]

    table = bigquery.Table(
        table_ref,
        schema=schema,
    )

    created_table = client.create_table(
        table,
        exists_ok=True,
    )

    print(
        "BigQuery table ready: "
        f"{created_table.full_table_id}"
    )

    return (
    f"{project_id}.{DATASET_ID}.{TABLE_ID}"
)



def manifest_to_rows(
    manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item in manifest:
        ledger = item["ledger_record"]

        rows.append(
            {
                "case_id": item["case_id"],
                "scenario": item["scenario"],
                "invoice_id": ledger["invoice_id"],
                "invoice_date": ledger["invoice_date"],
                "vendor": ledger["vendor"],
                "amount": float(ledger["amount"]),
                "currency": ledger["currency"],
                "quantity": int(ledger["quantity"]),
                "fx_rate": float(ledger["fx_rate"]),
                "line_items": json.dumps(ledger["line_items"]),
            }
        )

    return rows


def replace_table_rows(
    client: bigquery.Client,
    sql_table_id: str,
    rows: list[dict[str, Any]],
) -> None:
    """
    Clear then insert the evaluation ledger.

    This table is explicitly synthetic and rebuildable, so replacing
    rows is appropriate. Do not use this approach for the audit table.
    """
    delete_query = (
            f"DELETE FROM `{sql_table_id}` WHERE TRUE"
        )

    client.query(delete_query).result()

    errors = client.insert_rows_json(
            sql_table_id,
            rows,
        )

    if errors:
            raise RuntimeError(
                "Failed to insert synthetic evaluation ledger rows: "
                f"{errors}"
            )


def main() -> None:
    client = bigquery.Client()
    project_id = client.project

    manifest = load_manifest()
    sql_table_id = create_table(
        client=client,
        project_id=project_id,
    )

    rows = manifest_to_rows(manifest)

    replace_table_rows(
        client=client,
        sql_table_id=sql_table_id,
        rows=rows,
    )

    print(
        "Synthetic evaluation ledger loaded successfully."
    )

    print(f"Table: {sql_table_id}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()