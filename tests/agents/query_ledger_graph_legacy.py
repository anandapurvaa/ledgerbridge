# tests/agents/test_query_ledger_graph.py
from src.agents.graph_builder import build_reconciliation_graph

def test_query_ledger_graph():
    graph = build_reconciliation_graph()

    initial_state = {
        "user_query": "Show me recent invoices",
        "ledger_rows": [],
        "extracted_fields": {},
        "matched_ledger_records": [],
        "unmatched_cases": [],
        "hypotheses": [],
        "dispute_letter_draft": "",
    }

    result = graph.invoke(initial_state)

    print("Ledger rows returned:")
    for row in result["ledger_rows"]:
        print(row)

if __name__ == "__main__":
    test_query_ledger_graph()