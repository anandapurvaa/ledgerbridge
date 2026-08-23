# src/agents/investigator.py
from __future__ import annotations

from typing import Any


def money(
    value: float | int | None,
    currency: str,
) -> str:
    if value is None:
        return "unknown amount"

    return f"{float(value):,.2f} {currency}"


def investigate_reconciliation_result(
    extracted_fields: dict[str, Any],
    reconciliation_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Produce a deterministic, grounded investigation summary.

    All statements must be traceable to extracted invoice fields and
    reconciliation rule output; no LLM inference is used yet.
    """
    status = reconciliation_result.get(
        "status",
        "unmatched",
    )

    details = reconciliation_result.get(
        "discrepancy_details",
        {},
    )

    currency = extracted_fields.get(
        "currency",
        "EUR",
    )

    invoice_id = extracted_fields.get(
        "invoice_id",
        "UNKNOWN-INVOICE-ID",
    )

    vendor = extracted_fields.get(
        "vendor",
        "UNKNOWN-VENDOR",
    )

    amount = extracted_fields.get("amount")

    base = {
        "invoice_id": invoice_id,
        "vendor": vendor,
        "status": status,
        "evidence": details,
    }

    if status == "amount_mismatch":
        ledger_amount = details.get("ledger_amount")
        invoice_amount = details.get("invoice_amount")
        amount_delta = details.get("amount_delta")

        return {
            **base,
            "root_cause": "amount_mismatch",
            "severity": "high",
            "summary": (
                f"Invoice {invoice_id} from {vendor} shows "
                f"{money(invoice_amount, currency)}, while the ledger "
                f"record shows {money(ledger_amount, currency)}."
            ),
            "recommended_action": (
                "Hold payment or request a corrected invoice before "
                "approving the ledger amount."
            ),
            "dispute_reason": (
                f"Amount variance of "
                f"{money(amount_delta, currency)}."
            ),
        }

    if status == "quantity_mismatch":
        invoice_quantity = details.get(
            "invoice_quantity",
        )

        ledger_quantity = details.get(
            "ledger_quantity",
        )

        quantity_delta = details.get(
            "quantity_delta",
        )

        return {
            **base,
            "root_cause": "quantity_mismatch",
            "severity": "high",
            "summary": (
                f"Invoice {invoice_id} from {vendor} lists quantity "
                f"{invoice_quantity}, while the ledger record lists "
                f"{ledger_quantity}."
            ),
            "recommended_action": (
                "Request confirmation of delivered or billed quantity "
                "before payment approval."
            ),
            "dispute_reason": (
                f"Quantity variance of {quantity_delta} unit(s)."
            ),
        }

    if status == "fx_mismatch":
        invoice_fx_rate = details.get(
            "invoice_fx_rate",
        )

        ledger_fx_rate = details.get(
            "ledger_fx_rate",
        )

        relative_difference = details.get(
            "relative_fx_rate_difference",
        )

        percentage = (
            float(relative_difference) * 100
            if relative_difference is not None
            else 0.0
        )

        return {
            **base,
            "root_cause": "fx_mismatch",
            "severity": "medium",
            "summary": (
                f"Invoice {invoice_id} from {vendor} uses FX rate "
                f"{invoice_fx_rate}, while the ledger uses "
                f"{ledger_fx_rate}."
            ),
            "recommended_action": (
                "Validate the contracted exchange-rate source and "
                "request an updated invoice if the document rate is "
                "not applicable."
            ),
            "dispute_reason": (
                f"FX-rate variance of {percentage:.2f}%."
            ),
        }

    if status == "currency_mismatch":
        return {
            **base,
            "root_cause": "currency_mismatch",
            "severity": "high",
            "summary": (
                f"Invoice {invoice_id} from {vendor} uses currency "
                f"{details.get('invoice_currency')}, while the ledger "
                f"uses {details.get('ledger_currency')}."
            ),
            "recommended_action": (
                "Pause payment and confirm the contract currency with "
                "the vendor."
            ),
            "dispute_reason": "Invoice and ledger currencies differ.",
        }

    if status == "duplicate_charge":
        return {
            **base,
            "root_cause": "duplicate_charge",
            "severity": "high",
            "summary": (
                f"Invoice {invoice_id} from {vendor} appears to have "
                "already been reconciled successfully."
            ),
            "recommended_action": (
                "Block duplicate payment and confirm whether this is a "
                "resubmission, credit note, or separate billable event."
            ),
            "dispute_reason": (
                "Potential duplicate charge for an already processed "
                "invoice."
            ),
        }

    if status == "ambiguous":
        return {
            **base,
            "root_cause": "ambiguous_match",
            "severity": "medium",
            "summary": (
                f"Invoice {invoice_id} from {vendor} has multiple "
                "similar ledger candidates and cannot be matched "
                "reliably."
            ),
            "recommended_action": (
                "Route to an analyst to select the correct ledger "
                "record."
            ),
            "dispute_reason": (
                "Multiple possible ledger matches require review."
            ),
        }

    if status == "unmatched":
        return {
            **base,
            "root_cause": "unmatched_invoice",
            "severity": "medium",
            "summary": (
                f"Invoice {invoice_id} from {vendor} could not be "
                "matched to a valid ledger record."
            ),
            "recommended_action": (
                "Verify invoice identifier, vendor, date, and payment "
                "record before contacting the vendor."
            ),
            "dispute_reason": (
                "No matching ledger record was found."
            ),
        }

    return {
        **base,
        "root_cause": "no_action_required",
        "severity": "none",
        "summary": (
            f"Invoice {invoice_id} from {vendor} reconciled without "
            "a discrepancy."
        ),
        "recommended_action": "No action required.",
        "dispute_reason": "",
    }