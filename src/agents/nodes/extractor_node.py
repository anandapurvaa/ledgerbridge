# src/agents/nodes/extractor_node.py
from pathlib import Path

from src.agents.state import AgentState
from src.extraction.extraction_service import (
    extract_invoice_from_image,
)


def extractor_node(state: AgentState) -> dict:
    """
    Extract structured fields from a scanned invoice/receipt.

    Expected input:
        state["invoice_image_path"] = path to the uploaded image.
    """
    image_path = state.get("invoice_image_path")

    if not image_path:
        return {
            "extracted_fields": {},
            "reconciliation_result": {
                "status": "unmatched",
                "confidence": 0.0,
                "discrepancy_details": {
                    "reason": (
                        "No invoice_image_path was supplied to "
                        "the Extractor node."
                    )
                },
            },
        }

    if not Path(image_path).exists():
        return {
            "extracted_fields": {},
            "reconciliation_result": {
                "status": "unmatched",
                "confidence": 0.0,
                "discrepancy_details": {
                    "reason": (
                        f"Invoice image was not found: {image_path}"
                    )
                },
            },
        }

    extraction_result = extract_invoice_from_image(
        image_path,
    )

    return {
        "extracted_fields": extraction_result[
            "extracted_fields"
        ],
        "extraction_result": {
            "word_labels": extraction_result["word_labels"],
            "word_scores": extraction_result["word_scores"],
            "spans": [
                {
                    "entity_type": span.entity_type,
                    "text": span.text,
                    "score": span.score,
                    "start_word": span.start_word,
                    "end_word": span.end_word,
                }
                for span in extraction_result["spans"]
            ],
            "ocr_mean_confidence": extraction_result[
                "ocr_result"
            ]["mean_confidence"],
        },
    }