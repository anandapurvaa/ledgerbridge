from pathlib import Path

from src.agents.state import AgentState
from src.extraction.hybrid_extractor import (
    extract_invoice_hybrid,
)


def extractor_node(state: AgentState) -> dict:
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

    extraction = extract_invoice_hybrid(
        image_path=image_path,
        use_layoutlmv3=True,
    )

    layoutlmv3_result = extraction.get(
        "layoutlmv3_result"
    )

    return {
        "extracted_fields": extraction[
            "extracted_fields"
        ],
        "extraction_result": {
            "ocr_mean_confidence": extraction[
                "ocr_result"
            ]["mean_confidence"],
            "word_count": len(
                extraction["ocr_result"]["words"]
            ),
            "layoutlmv3_spans": [
                {
                    "entity_type": span.entity_type,
                    "text": span.text,
                    "score": span.score,
                    "start_word": span.start_word,
                    "end_word": span.end_word,
                }
                for span in (
                    layoutlmv3_result["spans"]
                    if layoutlmv3_result
                    else []
                )
            ],
        },
    }