from langgraph.graph import END, StateGraph

from src.agents.nodes.matcher_node import matcher_node
from src.agents.nodes.query_ledger_node import query_ledger_node
from src.agents.state import AgentState


def build_reconciliation_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("query_ledger", query_ledger_node)
    workflow.add_node("matcher", matcher_node)

    workflow.set_entry_point("query_ledger")
    workflow.add_edge("query_ledger", "matcher")
    workflow.add_edge("matcher", END)

    return workflow.compile()