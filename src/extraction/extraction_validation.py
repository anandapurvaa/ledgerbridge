# src/extraction/extraction_validation.py
from __future__ import annotations

import re
from typing import Any


def is_valid_invoice_id(value: str) -> bool:
    if not value:
        return False

    if value == "UNKNOWN-INVOICE-ID":
        return False

    return bool(
        re.fullmatch(
            r"[A-Z0-9][A-Z0-9_-]{3,}",
            value.upper(),
        )
    )


def is_valid_vendor(value: str) -> bool:
    if not value:
        return False

    if value == "UNKNOWN-VENDOR":
        return False

    letter_count = sum(
        character.isalpha()
        for character in value
    )

    return letter_count >= 3


def is_valid_date(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"\d{4}-\d{2}-\d{2}",
            str(value),
        )
    )


def is_valid_amount(value: Any) -> bool:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return False

    return 0 < amount < 10_000_000


def is_valid_currency(value: str) -> bool:
    return value in {
        "EUR",
        "USD",
        "GBP",
        "PLN",
        "MYR",
    }


def is_valid_quantity(value: Any) -> bool:
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return False

    return 1 <= quantity <= 10_000


def is_valid_fx_rate(value: Any) -> bool:
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return False

    return 0.01 <= rate <= 1000


def validate_extracted_fields(
    fields: dict[str, Any],
) -> dict[str, bool]:
    return {
        "invoice_id": is_valid_invoice_id(
            fields.get("invoice_id", "")
        ),
        "vendor": is_valid_vendor(
            fields.get("vendor", "")
        ),
        "invoice_date": is_valid_date(
            fields.get("invoice_date", "")
        ),
        "amount": is_valid_amount(
            fields.get("amount")
        ),
        "currency": is_valid_currency(
            fields.get("currency", "")
        ),
        "quantity": is_valid_quantity(
            fields.get("quantity")
        ),
        "fx_rate": is_valid_fx_rate(
            fields.get("fx_rate")
        ),
    }