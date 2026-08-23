# src/extraction/field_normalizer.py
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from src.extraction.entity_decoder import EntitySpan


CURRENCY_MARKERS = {
    "EUR": ("EUR", "€", "EURO"),
    "USD": ("USD", "US$", "$"),
    "GBP": ("GBP", "£"),
    "PLN": ("PLN", "ZŁ", "ZL"),
    "MYR": ("MYR", "RM"),
}


def normalize_currency(text: str) -> str:
    upper = text.upper()

    for currency, markers in CURRENCY_MARKERS.items():
        if any(marker in upper for marker in markers):
            return currency

    # SROIE receipts often use Malaysian Ringgit.
    return "MYR"


def normalize_amount(text: str) -> float | None:
    """
    Extract the last money-like number from an entity span and normalize
    European/US separators.

    Example:
      'ROUND TOTAL (RM): 1,234.56' → 1234.56
      'RM 9.00' → 9.0
    """
    matches = re.findall(
        r"-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})"
        r"|-?\d+[.,]\d{2}",
        text,
    )

    if not matches:
        return None

    value = matches[-1].replace(" ", "")

    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    else:
        value = value.replace(",", ".")

    try:
        return round(float(value), 2)
    except ValueError:
        return None


def normalize_date(text: str) -> str | None:
    """
    Parse numeric and abbreviated/month-name dates to ISO YYYY-MM-DD.
    """
    upper = re.sub(r"\s+", " ", text.upper().strip())

    patterns_and_formats = [
        (
            r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b",
            ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"),
        ),
        (
            r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b",
            (
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%d.%m.%Y",
                "%m-%d-%Y",
                "%m/%d/%Y",
                "%m.%d.%Y",
                "%d-%m-%y",
                "%d/%m/%y",
                "%m-%d-%y",
                "%m/%d/%y",
            ),
        ),
        (
            r"\b\d{1,2}\s+[A-Z]{3,9}\s+\d{2,4}\b",
            ("%d %b %Y", "%d %B %Y", "%d %b %y", "%d %B %y"),
        ),
        (
            r"\b[A-Z]{3,9}\s+\d{1,2},?\s+\d{2,4}\b",
            ("%b %d %Y", "%B %d %Y", "%b %d %y", "%B %d %y"),
        ),
    ]

    for pattern, formats in patterns_and_formats:
        match = re.search(pattern, upper)

        if not match:
            continue

        value = match.group(0).replace(",", "")

        for date_format in formats:
            try:
                return datetime.strptime(
                    value,
                    date_format,
                ).date().isoformat()
            except ValueError:
                continue

    return None


def choose_best_span(
    spans: Iterable[EntitySpan],
    entity_type: str,
) -> EntitySpan | None:
    candidates = [
        span
        for span in spans
        if span.entity_type == entity_type
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda span: span.score,
    )


def normalize_layoutlmv3_output(
    spans: list[EntitySpan],
    raw_text: str,
) -> dict:
    """
    Map model spans to the LedgerBridge structured extraction contract.
    """
    vendor_span = choose_best_span(spans, "VENDOR")
    date_span = choose_best_span(spans, "DATE")
    total_span = choose_best_span(spans, "TOTAL")

    vendor = (
        vendor_span.text.strip()
        if vendor_span
        else "UNKNOWN-VENDOR"
    )

    invoice_date = (
        normalize_date(date_span.text)
        if date_span
        else None
    )

    amount = (
        normalize_amount(total_span.text)
        if total_span
        else None
    )

    currency_source = (
        total_span.text
        if total_span
        else raw_text
    )

    confidence_values = [
        span.score
        for span in (
            vendor_span,
            date_span,
            total_span,
        )
        if span is not None
    ]

    return {
        "invoice_id": "UNKNOWN-INVOICE-ID",
        "invoice_date": invoice_date or "1970-01-01",
        "vendor": vendor,
        "amount": amount if amount is not None else 0.0,
        "currency": normalize_currency(currency_source),
        "quantity": 1,
        "fx_rate": 1.0,
        "line_items": [],
        "extraction_metadata": {
            "extractor": "layoutlmv3_lora",
            "overall_span_confidence": round(
                sum(confidence_values)
                / len(confidence_values),
                4,
            )
            if confidence_values
            else 0.0,
            "field_confidences": {
                "vendor": vendor_span.score if vendor_span else 0.0,
                "invoice_date": date_span.score if date_span else 0.0,
                "amount": total_span.score if total_span else 0.0,
            },
            "raw_spans": [
                {
                    "entity_type": span.entity_type,
                    "text": span.text,
                    "score": span.score,
                    "start_word": span.start_word,
                    "end_word": span.end_word,
                }
                for span in spans
            ],
        },
    }