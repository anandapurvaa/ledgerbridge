from src.agents.nodes.investigator_node import (
    investigator_node,
)
from src.agents.nodes.resolution_drafter_node import (
    resolution_drafter_node,
)


def test_investigator_node_returns_investigation_and_hypothesis(
    monkeypatch,
):
    expected_investigation = {
        "summary": "Invoice total differs from the ledger.",
        "root_cause": "amount_mismatch",
        "severity": "high",
        "recommended_action": "Hold payment.",
    }

    monkeypatch.setattr(
        "src.agents.nodes.investigator_node."
        "investigate_reconciliation_result",
        lambda extracted_fields, reconciliation_result: (
            expected_investigation
        ),
    )

    result = investigator_node(
        {
            "extracted_fields": {
                "invoice_id": "LB-INV-00001",
            },
            "reconciliation_result": {
                "status": "amount_mismatch",
            },
        }
    )

    assert result["investigation"] == expected_investigation

    assert result["hypotheses"] == [
        "Invoice total differs from the ledger.",
    ]


def test_resolution_drafter_returns_draft(
    monkeypatch,
):
    expected_draft = (
        "Subject: Request for clarification "
        "— Invoice LB-INV-00001"
    )

    monkeypatch.setattr(
        "src.agents.nodes.resolution_drafter_node."
        "draft_dispute_letter",
        lambda extracted_fields, investigation: expected_draft,
    )

    result = resolution_drafter_node(
        {
            "extracted_fields": {
                "invoice_id": "LB-INV-00001",
            },
            "investigation": {
                "root_cause": "amount_mismatch",
            },
        }
    )

    assert result == {
        "dispute_letter_draft": expected_draft,
    }