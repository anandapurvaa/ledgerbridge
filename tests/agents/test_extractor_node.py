# tests/agents/test_extractor_node.py
from src.agents.nodes.extractor_node import extractor_node


def test_extractor_node_returns_clear_error_without_path():
    result = extractor_node({})

    assert result["extracted_fields"] == {}
    assert (
        result["reconciliation_result"]["status"]
        == "unmatched"
    )