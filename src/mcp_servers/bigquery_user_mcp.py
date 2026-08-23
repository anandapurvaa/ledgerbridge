import asyncio
import json
import sys
from typing import Any

import mcp
from google.cloud import bigquery

Server = mcp.server.Server
Tool = mcp.types.Tool
TextContent = mcp.types.TextContent
stdio_server = mcp.stdio_server

server = Server("bigquery-user")
client = bigquery.Client()


def json_safe(value: Any) -> Any:
    """
    Convert BigQuery/Python values into JSON-compatible values.
    Dates, Decimals, and other uncommon types become strings.
    """
    return json.loads(json.dumps(value, default=str))


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_ledger",
            description=(
                "Run a read-only SQL SELECT query against the LedgerBridge "
                "BigQuery synthetic ledger."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A read-only BigQuery Standard SQL SELECT query.",
                    }
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "query_ledger":
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "ok": False,
                        "error": f"Unknown tool: {name}",
                        "rows": [],
                    }
                ),
            )
        ]

    query = arguments.get("query", "").strip()

    if not query:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "ok": False,
                        "error": "A non-empty SQL query is required.",
                        "rows": [],
                    }
                ),
            )
        ]

    if not query.upper().lstrip().startswith("SELECT"):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "ok": False,
                        "error": "Only read-only SELECT queries are permitted.",
                        "rows": [],
                    }
                ),
            )
        ]

    try:
        query_job = client.query(query)
        rows = [dict(row.items()) for row in query_job.result()]

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "ok": True,
                        "rows": json_safe(rows),
                    }
                ),
            )
        ]

    except Exception as exc:
        print(f"BigQuery query failed: {exc!r}", file=sys.stderr)

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "ok": False,
                        "error": str(exc),
                        "rows": [],
                    }
                ),
            )
        ]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())