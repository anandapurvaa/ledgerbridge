# src/extraction/ledger_aware_repair.py
from __future__ import annotations

from copy import deepcopy
from typing import Any


def relative_difference(
    left: float,
    right: float,
) -> float:
    if right == 0:
        return 0.0 if left == 0 else 1.0

    return abs(left - right) / abs(right)


def looks_like_prefixed_ocr_amount(
    extracted_amount: float,
    expected_amount: float,
) -> bool:
    """
    Detect common OCR prefix corruption:

      653.67  -> 1653.67
      587.91  -> 1587.91
      3190.45 -> 213190.45

    We do not repair normal business discrepancies such as:
      100.00 -> 137.50
    """
    extracted_text = f"{extracted_amount:.2f}"
    expected_text = f"{expected_amount:.2f}"

    if extracted_text.endswith(expected_text):
        prefix = extracted_text[
            : len(extracted_text) - len(expected_text)
        ]

        # Prefix must contain only digits and must be short enough to
        # look like OCR contamination, rather than a legitimate amount.
        if prefix.isdigit() and 1 <= len(prefix) <= 3:
            return True

    return False


def repair_extracted_fields(
    extracted_fields: dict[str, Any],
    ledger_candidate: dict[str, Any] | None,
    amount_repair_tolerance: float = 0.02,
) -> dict[str, Any]:
    """
    Apply conservative repairs based on a ledger candidate.

    Rules:
    - Only repair amount when it has an obvious numeric-prefix OCR error.
    - Only repair quantity when OCR fell back to 1 and ledger quantity
      is greater than 1.
    - Never repair invoice_id, vendor, date, or currency automatically.
    - Store every repair in extraction_metadata for auditability.
    """
    repaired = deepcopy(extracted_fields)

    metadata = repaired.setdefault(
        "extraction_metadata",
        {},
    )

    repairs: list[dict[str, Any]] = []

    if not ledger_candidate:
        metadata["ledger_aware_repairs"] = repairs
        return repaired

    expected_amount = float(
        ledger_candidate["amount"]
    )

    extracted_amount = float(
        repaired.get("amount", 0.0)
    )

    if (
        abs(extracted_amount - expected_amount)
        > amount_repair_tolerance
        and looks_like_prefixed_ocr_amount(
            extracted_amount=extracted_amount,
            expected_amount=expected_amount,
        )
    ):
        repairs.append(
            {
                "field": "amount",
                "original_value": extracted_amount,
                "repaired_value": expected_amount,
                "reason": (
                    "Detected numeric-prefix OCR corruption where "
                    "extracted amount ends with ledger amount."
                ),
            }
        )

        repaired["amount"] = expected_amount

    expected_quantity = int(
        ledger_candidate["quantity"]
    )

    extracted_quantity = int(
        repaired.get("quantity", 1)
    )

    if (
        extracted_quantity == 1
        and expected_quantity > 1
    ):
        repairs.append(
            {
                "field": "quantity",
                "original_value": extracted_quantity,
                "repaired_value": expected_quantity,
                "reason": (
                    "OCR quantity fell back to 1 while the candidate "
                    "ledger record has a higher quantity."
                ),
            }
        )

        repaired["quantity"] = expected_quantity

    metadata["ledger_aware_repairs"] = repairs

    return repaired