# src/agents/nodes/resolution_drafter_node.py
from src.agents.resolution_drafter import (
    draft_dispute_letter,
)
from src.agents.state import AgentState


def resolution_drafter_node(state: AgentState) -> dict:
    draft = draft_dispute_letter(
        extracted_fields=state.get(
            "extracted_fields",
            {},
        ),
        investigation=state.get(
            "investigation",
            {},
        ),
    )

    return {
        "dispute_letter_draft": draft,
    }