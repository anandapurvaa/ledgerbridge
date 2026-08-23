# src/extraction/ocr_reader.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output


def normalize_box(
    left: int,
    top: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
) -> list[int]:
    """
    Convert a pixel bounding box to LayoutLM-compatible 0–1000 coordinates.
    """
    x0 = max(0, min(1000, int(1000 * left / image_width)))
    y0 = max(0, min(1000, int(1000 * top / image_height)))
    x1 = max(0, min(1000, int(1000 * (left + width) / image_width)))
    y1 = max(0, min(1000, int(1000 * (top + height) / image_height)))

    return [x0, y0, x1, y1]


def prepare_image(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    return image

def build_lines(ocr_data: dict[str, list]) -> list[str]:
    grouped_words: dict[tuple[int, int, int], list[str]] = {}

    for index, raw_text in enumerate(ocr_data["text"]):
        text = raw_text.strip()

        if not text:
            continue

        line_key = (
            int(ocr_data["block_num"][index]),
            int(ocr_data["par_num"][index]),
            int(ocr_data["line_num"][index]),
        )

        grouped_words.setdefault(line_key, []).append(text)

    return [
        " ".join(words)
        for _, words in sorted(grouped_words.items())
    ]

def read_ocr(
    image_path: str | Path,
    min_confidence: float = 30.0,
) -> dict[str, Any]:
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image does not exist: {image_path}")

    image = prepare_image(Image.open(image_path))
    image_width, image_height = image.size

    ocr_data = pytesseract.image_to_data(
        image,
        output_type=Output.DICT,
        config="--oem 3 --psm 6",
    )

    words: list[str] = []
    boxes: list[list[int]] = []
    confidences: list[float] = []

    for index, raw_text in enumerate(ocr_data["text"]):
        text = raw_text.strip()

        try:
            confidence = float(ocr_data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1.0

        if not text or confidence < min_confidence:
            continue

        words.append(text)
        boxes.append(
            normalize_box(
                left=int(ocr_data["left"][index]),
                top=int(ocr_data["top"][index]),
                width=int(ocr_data["width"][index]),
                height=int(ocr_data["height"][index]),
                image_width=image_width,
                image_height=image_height,
            )
        )
        confidences.append(confidence)

    return {
        "image_path": str(image_path),
        "image_width": image_width,
        "image_height": image_height,
        "words": words,
        "boxes": boxes,
        "confidences": confidences,
        "lines": build_lines(ocr_data),
        "text": " ".join(words),
        "mean_confidence": (
            round(sum(confidences) / len(confidences), 2)
            if confidences
            else 0.0
        ),
    }