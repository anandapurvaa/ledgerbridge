import asyncio

from src.agents.nodes.query_ledger_node import call_query_ledger


PROJECT_ID = "cloudprojects-506123"
TABLE_ID = f"{PROJECT_ID}.ledgerbridge.invoices"


def test_query_ledger_returns_rows():
    rows = asyncio.run(
        call_query_ledger(
            f"""
            SELECT
                invoice_id,
                vendor,
                amount,
                currency,
                quantity,
                fx_rate
            FROM `{TABLE_ID}`
            LIMIT 5
            """
        )
    )

    assert rows
    assert len(rows) <= 5

    first_row = rows[0]

    assert "invoice_id" in first_row
    assert "vendor" in first_row
    assert "amount" in first_row


if __name__ == "__main__":
    test_query_ledger_returns_rows()
    print("MCP → BigQuery query test passed.")