import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters, stdio_client

from src.agents.state import AgentState


async def call_query_ledger(query: str) -> list[dict]:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["src/mcp_servers/bigquery_user_mcp.py"],
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            call_result = await session.call_tool(
                "query_ledger",
                arguments={"query": query},
            )

            if getattr(call_result, "isError", False):
                error_text = "\n".join(
                    getattr(content, "text", str(content))
                    for content in call_result.content
                )
                raise RuntimeError(f"MCP query_ledger error: {error_text}")

            for content in call_result.content:
                if not hasattr(content, "text"):
                    continue

                raw_text = content.text.strip()

                if not raw_text:
                    raise RuntimeError(
                        "MCP query_ledger returned an empty text response."
                    )

                try:
                    payload = json.loads(raw_text)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        "MCP query_ledger returned non-JSON content:\n"
                        f"{raw_text}"
                    ) from exc

                if not payload.get("ok", False):
                    raise RuntimeError(
                        "BigQuery MCP server returned an error:\n"
                        f"{payload.get('error', 'Unknown server error')}"
                    )

                return payload.get("rows", [])

    raise RuntimeError(
        "MCP query_ledger returned no text content blocks."
    )


def query_ledger_node(state: AgentState) -> dict:
    table_id = state.get(
        "ledger_table_id",
        "cloudprojects-506123.ledgerbridge.invoices",
    )

    query = f"""
        SELECT
            invoice_id,
            invoice_date,
            vendor,
            amount,
            currency,
            quantity,
            fx_rate,
            line_items
        FROM `{table_id}`
        LIMIT 500
    """

    rows = asyncio.run(call_query_ledger(query))

    return {
        "ledger_rows": rows,
    }