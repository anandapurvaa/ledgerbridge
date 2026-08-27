from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, StateGraph

from src.agents.graph_routes import (
    route_after_duplicate_detection,
    route_after_extractor,
)
from src.agents.nodes.audit_writer_node import (
    audit_writer_node as base_audit_writer_node,
)
from src.agents.nodes.duplicate_detection_node import (
    duplicate_detection_node as base_duplicate_detection_node,
)
from src.agents.nodes.extractor_node import (
    extractor_node as base_extractor_node,
)
from src.agents.nodes.investigator_node import (
    investigator_node as base_investigator_node,
)
from src.agents.nodes.matcher_node import (
    matcher_node as base_matcher_node,
)
from src.agents.nodes.query_ledger_node import (
    query_ledger_node as base_query_ledger_node,
)
from src.agents.nodes.resolution_drafter_node import (
    resolution_drafter_node as base_resolution_drafter_node,
)
from src.agents.state import AgentState


def _timed_node(name: str, base_fn):
    """
    Wrap a node function to print how long it took.
    """
    def wrapper(state: dict[str, Any]) -> dict[str, Any]:
        t0 = time.time()
        result = base_fn(state)
        t1 = time.time()
        print(f"[NODE {name}] {t1 - t0:.2f}s")
        return result
    return wrapper


def build_reconciliation_graph():
    """
    Full invoice-image reconciliation workflow.

    Input:
        invoice_image_path

    Output:
        extracted fields, candidate ledger records, reconciliation result,
        investigation, optional dispute draft, and BigQuery audit event ID.
    """
    # Wrap each node with timing
    extractor_node = _timed_node("extractor", base_extractor_node)
    query_ledger_node = _timed_node("query_ledger", base_query_ledger_node)
    matcher_node = _timed_node("matcher", base_matcher_node)
    duplicate_detection_node = _timed_node(
        "duplicate_detection",
        base_duplicate_detection_node,
    )
    investigator_node = _timed_node("investigator", base_investigator_node)
    resolution_drafter_node = _timed_node(
        "resolution_drafter",
        base_resolution_drafter_node,
    )
    audit_writer_node = _timed_node("write_audit", base_audit_writer_node)

    workflow = StateGraph(AgentState)

    workflow.add_node("extractor", extractor_node)
    workflow.add_node("query_ledger", query_ledger_node)
    workflow.add_node("matcher", matcher_node)
    workflow.add_node(
        "duplicate_detection",
        duplicate_detection_node,
    )
    workflow.add_node("investigator", investigator_node)
    workflow.add_node(
        "resolution_drafter",
        resolution_drafter_node,
    )
    workflow.add_node("write_audit", audit_writer_node)

    workflow.set_entry_point("extractor")

    workflow.add_conditional_edges(
        "extractor",
        route_after_extractor,
        {
            "query_ledger": "query_ledger",
            "investigator": "investigator",
        },
    )

    workflow.add_edge("query_ledger", "matcher")
    workflow.add_edge("matcher", "duplicate_detection")

    workflow.add_conditional_edges(
        "duplicate_detection",
        route_after_duplicate_detection,
        {
            "write_audit": "write_audit",
            "investigator": "investigator",
        },
    )

    workflow.add_edge(
        "investigator",
        "resolution_drafter",
    )

    workflow.add_edge(
        "resolution_drafter",
        "write_audit",
    )

    workflow.add_edge("write_audit", END)

    return workflow.compile()