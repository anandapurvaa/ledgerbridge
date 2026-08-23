# src/extraction/hybrid_extractor.py
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image

from src.extraction.extraction_validation import (
    validate_extracted_fields,
)
from src.extraction.heuristic_extractor import (
    extract_fields_from_ocr,
)
from src.extraction.layoutlmv3_inference import (
    LayoutLMv3Extractor,
)
from src.extraction.ocr_reader import read_ocr


@lru_cache(maxsize=1)
def get_layoutlmv3_extractor() -> LayoutLMv3Extractor:
    """
    Keep model weights loaded once per process.

    The model is secondary evidence for now, but loading it once is
    essential for later Cloud Run use.
    """
    return LayoutLMv3Extractor(
        model_dir="models/layoutlmv3_lora_weighted",
    )


def extract_invoice_hybrid(
    image_path: str | Path,
    use_layoutlmv3: bool = True,
) -> dict[str, Any]:
    """
    Hybrid document extraction.

    OCR heuristics provide the structured reconciliation-critical schema.
    LayoutLMv3 predictions are retained as evidence and become field-level
    fallbacks only if a heuristic value fails validation.
    """
    image_path = Path(image_path)

    ocr_result = read_ocr(image_path)

    heuristic_fields = extract_fields_from_ocr(
        ocr_result
    )

    validation = validate_extracted_fields(
        heuristic_fields
    )

    model_result: dict[str, Any] | None = None
    model_fields: dict[str, Any] = {}

    if use_layoutlmv3:
        image = Image.open(image_path).convert("RGB")

        model_result = get_layoutlmv3_extractor().predict(
            image=image,
            words=ocr_result["words"],
            bboxes=ocr_result["boxes"],
        )

        model_fields = model_result["extracted_fields"]

    final_fields = dict(heuristic_fields)

    # LayoutLMv3 is only allowed to fill fields it learned on SROIE.
    # It cannot repair invoice ID, currency, quantity, or FX rate.
    model_fallback_fields = (
        "vendor",
        "invoice_date",
        "amount",
    )

    applied_fallbacks: list[dict[str, Any]] = []

    for field_name in model_fallback_fields:
        if validation.get(field_name, False):
            continue

        candidate_value = model_fields.get(field_name)

        candidate_fields = {
            **final_fields,
            field_name: candidate_value,
        }

        candidate_validation = validate_extracted_fields(
            candidate_fields
        )

        if candidate_validation.get(field_name, False):
            applied_fallbacks.append(
                {
                    "field": field_name,
                    "original_value": final_fields.get(
                        field_name
                    ),
                    "fallback_value": candidate_value,
                    "source": "layoutlmv3_lora",
                }
            )

            final_fields[field_name] = candidate_value

    heuristic_metadata = final_fields.setdefault(
        "extraction_metadata",
        {},
    )

    heuristic_metadata.update(
        {
            "extractor": "hybrid_ocr_layoutlmv3",
            "heuristic_field_validation": validation,
            "layoutlmv3_enabled": use_layoutlmv3,
            "layoutlmv3_fallbacks": applied_fallbacks,
            "layoutlmv3_fields": model_fields,
        }
    )

    return {
        "extracted_fields": final_fields,
        "ocr_result": ocr_result,
        "layoutlmv3_result": model_result,
    }