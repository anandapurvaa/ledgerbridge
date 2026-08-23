# tests/ui/test_graph_runner.py
from src.ui.graph_runner import run_reconciliation_graph


def test_graph_runner_returns_structured_result():
    result = run_reconciliation_graph(
        invoice_image_path=(
            "data/synthetic/invoice_images/"
            "amount_mismatch_00023.png"
        )
    )

    assert "extracted_fields" in result
    assert "reconciliation_result" in result
    assert "dispute_letter_draft" in result
    assert "audit_event_id" in result