# src/agents/nodes/investigator_node.py
from src.agents.investigator import (
    investigate_reconciliation_result,
)
from src.agents.state import AgentState


def investigator_node(state: AgentState) -> dict:
    investigation = investigate_reconciliation_result(
        extracted_fields=state.get(
            "extracted_fields",
            {},
        ),
        reconciliation_result=state.get(
            "reconciliation_result",
            {},
        ),
    )

    return {
        "investigation": investigation,
        "hypotheses": [
            investigation["summary"],
        ],
    }