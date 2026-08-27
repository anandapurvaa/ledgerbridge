# src/agents/nodes/query_ledger_node.py
from __future__ import annotations

from typing import Any

from google.cloud import bigquery

from src.agents.state import AgentState


def query_ledger_node(state: AgentState) -> dict:
    table_id = state.get(
        "ledger_table_id",
        "cloudprojects-506123.ledgerbridge.invoices_clustered",
    )

    extracted_fields = state.get("extracted_fields", {})
    vendor = extracted_fields.get("vendor")

    # Build an optional WHERE clause filtering by vendor if available.
    where_sql = ""
    if vendor:
        # Simple escaping: replace single quotes with two single quotes.
        vendor_safe = str(vendor).replace("'", "''")
        where_sql = f"WHERE vendor = '{vendor_safe}'"

    query = f"""
        SELECT
            invoice_id,
            invoice_date,
            vendor,
            amount,
            currency,
            quantity,
            fx_rate
        FROM `{table_id}`
        {where_sql}
        LIMIT 60
    """

    client = bigquery.Client()
    rows = list(client.query(query).result())
    ledger_rows = [dict(row) for row in rows]

    return {
        "ledger_rows": ledger_rows,
    }