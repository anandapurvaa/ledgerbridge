from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from rapidfuzz import fuzz


CURRENCIES = {
    "EUR": ["EUR", "€", "EURO"],
    "USD": ["USD", "US$", "$"],
    "GBP": ["GBP", "£"],
    "PLN": ["PLN", "ZŁ", "ZL"],
    "MYR": ["MYR", "RM"],
}

TOTAL_KEYWORDS = [
    "TOTAL DUE",
    "GRAND TOTAL",
    "TOTAL AMOUNT",
    "AMOUNT DUE",
    "TOTAL",
    "NET TOTAL",
    "BALANCE DUE",
]

INVOICE_ID_PATTERNS = [
    # Synthetic LedgerBridge format:
    # Invoice No.: LB-INV-00001
    r"(?:INVOICE\s*(?:NO\.?|NUMBER|#|ID)?\s*[:#-]?\s*)"
    r"([A-Z]{1,10}[-_][A-Z0-9_-]{3,})",

    # Generic format:
    r"(?:INVOICE|INV|RECEIPT|BILL)"
    r"\s*(?:NO\.?|NUMBER|#|ID)?\s*[:#-]?\s*"
    r"([A-Z0-9][A-Z0-9/_-]{2,})",

    # Standalone invoice-like ID:
    r"\b([A-Z]{2,12}(?:[-_/][A-Z0-9]{2,})+)\b",
]

DATE_PATTERNS = [
    r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b",
    r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b",
    r"\b\d{1,2}\s+[A-Z]{3,9}\s+\d{2,4}\b",
]

MONEY_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:€|\$|£|RM|MYR)?\s*"
    r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})"
    r"|\d+[.,]\d{2})"
    r"\s*(?:EUR|USD|GBP|PLN|MYR|RM|€|\$|£|ZŁ)?",
    flags=re.IGNORECASE,
)


def normalize_line(line: str) -> str:
    return " ".join(line.upper().split())


def parse_amount(raw_amount: str) -> float | None:
    value = raw_amount.strip().replace(" ", "")

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


def detect_currency(text: str) -> str:
    upper_text = text.upper()

    # Prefer explicit three-letter currency codes over generic symbols.
    for currency in ("EUR", "USD", "GBP", "PLN", "MYR"):
        if re.search(
            rf"\b{currency}\b",
            upper_text,
        ):
            return currency

    for currency, markers in CURRENCIES.items():
        if any(marker in upper_text for marker in markers):
            return currency

    return "EUR"


def extract_invoice_id(text: str) -> str:
    upper_text = text.upper()

    for pattern in INVOICE_ID_PATTERNS:
        match = re.search(
            pattern,
            upper_text,
            flags=re.IGNORECASE,
        )

        if match:
            candidate = match.group(1)

            candidate = re.sub(
                r"[^A-Z0-9_-]",
                "",
                candidate,
            )

            if len(candidate) >= 4:
                return candidate

    return "UNKNOWN-INVOICE-ID"


def extract_date(text: str) -> str:
    upper_text = text.upper()

    for pattern in DATE_PATTERNS:
        match = re.search(pattern, upper_text)

        if not match:
            continue

        raw_date = match.group(0)

        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d.%m.%Y",
            "%m-%d-%Y",
            "%m/%d/%Y",
            "%m.%d.%Y",
            "%d %b %Y",
            "%d %B %Y",
        ]

        for date_format in date_formats:
            try:
                return datetime.strptime(
                    raw_date,
                    date_format,
                ).date().isoformat()
            except ValueError:
                continue

    return "1970-01-01"


def extract_vendor(lines: list[str]) -> str:
    """
    Synthetic invoices place the vendor in the first header line.
    Preserve the generic fallback for real receipts.
    """
    if lines:
        first_line = lines[0].strip()

        if (
            len(first_line) >= 3
            and "INVOICE" not in first_line.upper()
        ):
            return first_line[:120]

    ignored_terms = (
        "INVOICE",
        "RECEIPT",
        "DATE",
        "TOTAL",
        "TAX",
        "CASH",
        "VISA",
        "MASTERCARD",
        "THANK",
        "DESCRIPTION",
        "PAYMENT",
    )

    for line in lines[:10]:
        cleaned = line.strip()

        if len(cleaned) < 3:
            continue

        if any(
            term in cleaned.upper()
            for term in ignored_terms
        ):
            continue

        if sum(
            character.isalpha()
            for character in cleaned
        ) >= 3:
            return cleaned[:120]

    return "UNKNOWN-VENDOR"


def score_total_line(line: str) -> float:
    upper_line = normalize_line(line)

    keyword_score = max(
        [
            fuzz.partial_ratio(
                keyword,
                upper_line,
            )
            for keyword in TOTAL_KEYWORDS
        ],
        default=0,
    )

    has_money = bool(MONEY_PATTERN.search(line))

    # Prefer explicit TOTAL DUE over similar subtotal/tax lines.
    if "TOTAL DUE" in upper_line:
        keyword_score += 100

    if "SUBTOTAL" in upper_line:
        keyword_score -= 40

    if "TAX" in upper_line:
        keyword_score -= 40

    return keyword_score + (
        20 if has_money else 0
    )


def extract_total(lines: list[str]) -> float:
    scored_lines = sorted(
        (
            (score_total_line(line), line)
            for line in lines
        ),
        reverse=True,
    )

    for score, line in scored_lines:
        if score < 65:
            continue

        values = MONEY_PATTERN.findall(line)

        if values:
            amount = parse_amount(values[-1])

            if amount is not None:
                return amount

    all_amounts: list[float] = []

    for line in lines:
        for raw_value in MONEY_PATTERN.findall(line):
            amount = parse_amount(raw_value)

            if amount is not None:
                all_amounts.append(amount)

    return max(all_amounts) if all_amounts else 0.0


def extract_quantity(lines: list[str]) -> int:
    """
    Extract quantity from a synthetic LedgerBridge invoice line item.

    OCR may render a table row as:
    Cloud platform support 9 112.14 € 1,009.26 €
    """
    header_index: int | None = None

    for index, line in enumerate(lines):
        normalized = normalize_line(line)

        if (
            "DESCRIPTION" in normalized
            and (
                "QTY" in normalized
                or "QUANTITY" in normalized
            )
        ):
            header_index = index
            break

    if header_index is not None:
        stop_terms = (
            "SUBTOTAL",
            "TAX",
            "TOTAL",
            "PAYMENT",
            "PLEASE",
            "GENERATED",
        )

        for row_line in lines[header_index + 1:]:
            normalized = normalize_line(row_line)

            if any(
                term in normalized
                for term in stop_terms
            ):
                break

            # Capture isolated whole numbers only; skip decimal amounts.
            integer_candidates = re.findall(
                r"(?<![.\d])\b(\d{1,3})\b(?![.\d])",
                row_line,
            )

            for candidate in integer_candidates:
                quantity = int(candidate)

                if 1 <= quantity <= 999:
                    return quantity

    # Fallback for "Qty: 4" layouts.
    for line in lines:
        inline_match = re.search(
            r"\b(?:QTY|QUANTITY)\s*[:=]?\s*(\d{1,4})\b",
            line,
            flags=re.IGNORECASE,
        )

        if inline_match:
            quantity = int(inline_match.group(1))

            if quantity > 0:
                return quantity

    return 1

def extract_fx_rate(lines: list[str]) -> float:
    """
    Extract the displayed FX rate from invoice metadata.

    Expected layouts:
      FX Rate: 1.0123
      FX RATE 0.9611
      Exchange Rate: 1.1504

    Fallback is 1.0, appropriate for EUR/native-currency invoices
    when no explicit rate is available.
    """
    for line in lines:
        match = re.search(
            r"\b(?:FX\s*RATE|EXCHANGE\s*RATE)"
            r"\s*[:=]?\s*"
            r"(\d+(?:[.,]\d{1,6})?)\b",
            line,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        raw_value = match.group(1).replace(",", ".")

        try:
            rate = float(raw_value)

            if 0.01 <= rate <= 1000:
                return round(rate, 4)

        except ValueError:
            continue

    return 1.0


def extract_fields_from_ocr(
    ocr_result: dict[str, Any],
) -> dict[str, Any]:
    text = ocr_result.get("text", "")

    lines = ocr_result.get("lines", [])

    if not lines and ocr_result.get("words"):
        words = ocr_result["words"]

        lines = [
            " ".join(words[index:index + 8])
            for index in range(0, len(words), 8)
        ]

    currency = detect_currency(text)

    return {
        "invoice_id": extract_invoice_id(text),
        "invoice_date": extract_date(text),
        "vendor": extract_vendor(lines),
        "amount": extract_total(lines),
        "currency": currency,
        "quantity": extract_quantity(lines),
        "fx_rate": extract_fx_rate(lines),
        "line_items": [],
        "extraction_metadata": {
            "extractor": "heuristic_ocr_v2",
            "ocr_mean_confidence": ocr_result.get(
                "mean_confidence",
                0.0,
            ),
            "raw_text": text,
            "ocr_lines": lines,
        },
    }