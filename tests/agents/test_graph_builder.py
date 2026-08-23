from src.agents.graph_builder import (
    build_reconciliation_graph,
)


def test_graph_compiles():
    graph = build_reconciliation_graph()

    assert graph is not None


def test_graph_contains_all_expected_nodes():
    graph = build_reconciliation_graph()

    graph_definition = graph.get_graph()

    node_names = set(graph_definition.nodes.keys())

    expected_nodes = {
        "extractor",
        "query_ledger",
        "matcher",
        "duplicate_detection",
        "investigator",
        "resolution_drafter",
        "write_audit",
    }

    assert expected_nodes.issubset(node_names)