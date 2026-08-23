from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image

from src.extraction.layoutlmv3_inference import (
    LayoutLMv3Extractor,
)
from src.extraction.ocr_reader import read_ocr


@lru_cache(maxsize=1)
def get_extractor() -> LayoutLMv3Extractor:
    """
    Load model once per process instead of loading 500 MB weights for
    every invoice request.
    """
    return LayoutLMv3Extractor()


def extract_invoice_from_image(
    image_path: str | Path,
) -> dict[str, Any]:
    image_path = Path(image_path)

    ocr_result = read_ocr(image_path)

    image = Image.open(image_path).convert("RGB")

    prediction = get_extractor().predict(
        image=image,
        words=ocr_result["words"],
        bboxes=ocr_result["boxes"],
    )

    prediction["ocr_result"] = ocr_result

    return prediction