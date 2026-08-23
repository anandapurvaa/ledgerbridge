from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from rapidfuzz import fuzz


LABEL_LIST = [
    "O",
    "B-VENDOR",
    "I-VENDOR",
    "B-DATE",
    "I-DATE",
    "B-TOTAL",
    "I-TOTAL",
]

LABEL_TO_ID = {
    label: index
    for index, label in enumerate(LABEL_LIST)
}

ID_TO_LABEL = {
    index: label
    for label, index in LABEL_TO_ID.items()
}


def normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_numeric(value: str) -> str:
    """
    Normalize money-like numeric strings for comparisons.

    Examples:
      RM 9.00      -> 9.00
      1,234.56     -> 1234.56
      1.234,56     -> 1234.56
    """
    value = value.strip().upper()
    value = re.sub(r"(RM|EUR|USD|GBP|MYR|SGD)", "", value)
    value = re.sub(r"[^0-9,.\-]", "", value)

    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    else:
        value = value.replace(",", ".")

    try:
        return f"{float(value):.2f}"
    except ValueError:
        return ""


def parse_date_to_iso(value: str) -> str:
    """
    Return YYYY-MM-DD from noisy receipt dates.

    Supported examples:
      25/12/2018              -> 2018-12-25
      12/28/2017              -> 2017-12-28
      05 MAR 2018             -> 2018-03-05
      05 MAR 2018 18:24       -> 2018-03-05
      2017-12-28 22:17PM      -> 2017-12-28
      2018.03.05              -> 2018-03-05
    """
    value = value.strip().upper()
    value = re.sub(r"\s+", " ", value)

    # Month-name formats must be checked before numeric formats.
    month_name_patterns = [
        r"\b\d{1,2}\s+[A-Z]{3,9}\s+\d{2,4}\b",
        r"\b[A-Z]{3,9}\s+\d{1,2},?\s+\d{2,4}\b",
    ]

    month_name_formats = [
        "%d %b %Y",
        "%d %B %Y",
        "%d %b %y",
        "%d %B %y",
        "%b %d %Y",
        "%B %d %Y",
        "%b %d %y",
        "%B %d %y",
    ]

    for pattern in month_name_patterns:
        match = re.search(pattern, value)

        if not match:
            continue

        candidate = match.group(0).replace(",", "")

        for date_format in month_name_formats:
            try:
                return datetime.strptime(
                    candidate,
                    date_format,
                ).date().isoformat()
            except ValueError:
                continue

    # ISO year-month-day formats.
    iso_patterns = [
        r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b",
    ]

    iso_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
    ]

    for pattern in iso_patterns:
        match = re.search(pattern, value)

        if not match:
            continue

        candidate = match.group(0)

        for date_format in iso_formats:
            try:
                return datetime.strptime(
                    candidate,
                    date_format,
                ).date().isoformat()
            except ValueError:
                continue

    # Ambiguous numeric formats.
    #
    # We first attempt DD/MM/YYYY, then MM/DD/YYYY. For 12/28/2017,
    # DD/MM fails because 28 cannot be a month; MM/DD then succeeds.
    numeric_patterns = [
        r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b",
    ]

    numeric_formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d-%m-%y",
        "%d/%m/%y",
        "%d.%m.%y",
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%m.%d.%Y",
        "%m-%d-%y",
        "%m/%d/%y",
        "%m.%d.%y",
    ]

    for pattern in numeric_patterns:
        match = re.search(pattern, value)

        if not match:
            continue

        candidate = match.group(0)

        for date_format in numeric_formats:
            try:
                return datetime.strptime(
                    candidate,
                    date_format,
                ).date().isoformat()
            except ValueError:
                continue

    return ""


def is_date_match(
    word: str,
    entity_value: str,
) -> bool:
    entity_date = parse_date_to_iso(entity_value)
    word_date = parse_date_to_iso(word)

    if not entity_date or not word_date:
        return False

    return entity_date == word_date


def is_total_match(
    word: str,
    entity_value: str,
) -> bool:
    normalized_word = normalize_numeric(word)
    normalized_entity = normalize_numeric(entity_value)

    if not normalized_word or not normalized_entity:
        return False

    return normalized_word == normalized_entity


def is_vendor_match(
    word: str,
    entity_value: str,
    threshold: int = 86,
) -> bool:
    """
    Match noisy receipt company words/lines against the company entity.

    1. Exact normalized containment is preferred.
    2. Fuzzy partial matching recovers OCR character errors:
       BND vs BHD, missing spaces, periods, etc.
    """
    normalized_word = normalize_text(word)
    normalized_entity = normalize_text(entity_value)

    if not normalized_word or not normalized_entity:
        return False

    if normalized_word in normalized_entity:
        return True

    if len(normalized_word) < 4:
        return False

    score = fuzz.partial_ratio(
        normalized_word,
        normalized_entity,
    )

    return score >= threshold


def find_entity_word_indices(
    words: list[str],
    entity_value: str,
    entity_type: str,
) -> set[int]:
    matching_indices: set[int] = set()

    for index, word in enumerate(words):
        if entity_type == "DATE":
            is_match = is_date_match(word, entity_value)

        elif entity_type == "TOTAL":
            is_match = is_total_match(word, entity_value)

        elif entity_type == "VENDOR":
            is_match = is_vendor_match(word, entity_value)

        else:
            raise ValueError(
                f"Unsupported entity type: {entity_type}"
            )

        if is_match:
            matching_indices.add(index)

    return matching_indices


def assign_bio_labels(
    words: list[str],
    entities: dict[str, str],
) -> list[str]:
    """
    Generate word-level BIO labels for the reconciliation-critical fields.

    Process totals and dates before vendors so a broad vendor fuzzy match
    never overwrites a numeric/date entity.
    """
    labels = ["O"] * len(words)

    entity_to_label = [
        ("total", "TOTAL"),
        ("date", "DATE"),
        ("company", "VENDOR"),
    ]

    for entity_key, entity_type in entity_to_label:
        entity_value = entities.get(entity_key, "")

        indices = sorted(
            find_entity_word_indices(
                words=words,
                entity_value=entity_value,
                entity_type=entity_type,
            )
        )

        for position, word_index in enumerate(indices):
            labels[word_index] = (
                f"B-{entity_type}"
                if position == 0
                else f"I-{entity_type}"
            )

    return labels


def normalize_bbox(
    bbox: list[int],
    image_width: int,
    image_height: int,
) -> list[int]:
    x0, y0, x1, y1 = bbox

    normalized = [
        int(1000 * x0 / image_width),
        int(1000 * y0 / image_height),
        int(1000 * x1 / image_width),
        int(1000 * y1 / image_height),
    ]

    normalized = [
        max(0, min(1000, value))
        for value in normalized
    ]

    x0_n, y0_n, x1_n, y1_n = normalized

    return [
        min(x0_n, x1_n),
        min(y0_n, y1_n),
        max(x0_n, x1_n),
        max(y0_n, y1_n),
    ]


def normalize_bboxes(
    bboxes: list[list[int]],
    image_size: dict[str, int],
) -> list[list[int]]:
    width = int(image_size["width"])
    height = int(image_size["height"])

    if width <= 0 or height <= 0:
        raise ValueError(
            "Image width and height must both be positive."
        )

    return [
        normalize_bbox(
            bbox=bbox,
            image_width=width,
            image_height=height,
        )
        for bbox in bboxes
    ]


def preprocess_sroie_sample(
    sample: dict[str, Any],
) -> dict[str, Any]:
    words = sample["words"]
    bboxes = sample["bboxes"]
    entities = sample["entities"]
    image_size = sample["image_size"]

    if len(words) != len(bboxes):
        raise ValueError(
            "SROIE sample has different word and bbox counts: "
            f"{len(words)} words vs {len(bboxes)} boxes."
        )

    labels = assign_bio_labels(
        words=words,
        entities=entities,
    )

    normalized_boxes = normalize_bboxes(
        bboxes=bboxes,
        image_size=image_size,
    )

    label_ids = [
        LABEL_TO_ID[label]
        for label in labels
    ]

    return {
        "image": sample["image"],
        "key": sample["key"],
        "words": words,
        "bboxes": normalized_boxes,
        "labels": label_ids,
        "label_names": labels,
        "entities": entities,
    }