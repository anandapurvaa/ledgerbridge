# src/data/create_audit_schema.py
from google.cloud import bigquery


client = bigquery.Client()

PROJECT_ID = client.project
DATASET_ID = "ledgerbridge"
TABLE_ID = "reconciliation_audit"


def create_audit_table() -> None:
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    client.create_dataset(dataset_ref, exists_ok=True)

    table_ref = dataset_ref.table(TABLE_ID)

    schema = [
        bigquery.SchemaField(
            "audit_event_id",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "event_timestamp",
            "TIMESTAMP",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "invoice_id",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "vendor",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "invoice_date",
            "DATE",
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
            "reconciliation_status",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "matched_ledger_invoice_id",
            "STRING",
            mode="NULLABLE",
        ),
        bigquery.SchemaField(
            "run_id",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "source",
            "STRING",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "details_json",
            "JSON",
            mode="NULLABLE",
        ),
    ]

    table = bigquery.Table(table_ref, schema=schema)

    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="event_timestamp",
    )

    table.clustering_fields = [
        "invoice_id",
        "vendor",
        "reconciliation_status",
    ]

    created_table = client.create_table(
        table,
        exists_ok=True,
    )

    print(f"Audit table ready: {created_table.full_table_id}")


if __name__ == "__main__":
    create_audit_table()