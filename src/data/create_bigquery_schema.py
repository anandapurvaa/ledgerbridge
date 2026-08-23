# src/data/create_bigquery_schema.py
from google.cloud import bigquery

# Uses ADC (gcloud login); no service account key needed
client = bigquery.Client()

PROJECT_ID = client.project  # your current gcloud project
DATASET_ID = "ledgerbridge"
TABLE_ID = "invoices"

def create_dataset_and_table():
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    try:
        dataset = client.create_dataset(dataset_ref, exists_ok=True)
        print(f"Dataset {dataset.dataset_id} created/exists.")
    except Exception as e:
        print("Error creating dataset:", e)
        return

    table_ref = dataset_ref.table(TABLE_ID)
    schema = [
        bigquery.SchemaField("invoice_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("invoice_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("vendor", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("amount", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("currency", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("quantity", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("fx_rate", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("line_items", "JSON", mode="NULLABLE"),
    ]

    table = bigquery.Table(table_ref, schema=schema)
    try:
        table = client.create_table(table, exists_ok=True)
        print(f"Table {table.full_table_id} created/exists.")
    except Exception as e:
        print("Error creating table:", e)

if __name__ == "__main__":
    create_dataset_and_table()