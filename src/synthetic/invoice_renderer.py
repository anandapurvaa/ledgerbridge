# src/synthetic/invoice_renderer.py
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


PAGE_WIDTH = 1240
PAGE_HEIGHT = 1754
MARGIN = 85

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/verdana.ttf",
]

BOLD_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
]


def load_font(
    size: int,
    bold: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        BOLD_FONT_CANDIDATES
        if bold
        else FONT_CANDIDATES
    )

    for candidate in candidates:
        font_path = Path(candidate)

        if font_path.exists():
            return ImageFont.truetype(
                str(font_path),
                size=size,
            )

    return ImageFont.load_default()


def money(value: float, currency: str) -> str:
    symbols = {
        "EUR": "€",
        "USD": "$",
        "GBP": "£",
        "PLN": "zł",
    }

    symbol = symbols.get(currency, currency)

    if currency == "EUR":
        return f"{value:,.2f} {symbol}"

    return f"{symbol}{value:,.2f}"


def build_line_items(
    invoice: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_line_items = invoice.get("line_items")

    if isinstance(raw_line_items, str):
        try:
            import json

            raw_line_items = json.loads(raw_line_items)
        except Exception:
            raw_line_items = None

    if isinstance(raw_line_items, list) and raw_line_items:
        parsed_items = []

        for item in raw_line_items:
            quantity = int(
                item.get(
                    "qty",
                    item.get("quantity", invoice["quantity"]),
                )
            )

            price = float(
                item.get(
                    "price",
                    item.get(
                        "unit_price",
                        invoice["amount"] / max(quantity, 1),
                    ),
                )
            )

            parsed_items.append(
                {
                    "description": item.get(
                        "desc",
                        item.get(
                            "description",
                            "Professional services",
                        ),
                    ),
                    "quantity": quantity,
                    "unit_price": price,
                }
            )

        return parsed_items

    quantity = int(invoice["quantity"])
    fx_rate = float(invoice.get("fx_rate", 1.0))

    unit_price = round(
        float(invoice["amount"])
        / max(quantity * fx_rate, 1),
        2,
    )

    return [
        {
            "description": "Professional services",
            "quantity": quantity,
            "unit_price": unit_price,
        }
    ]


def render_invoice(
    invoice: dict[str, Any],
    output_path: str | Path,
    seed: int | None = None,
) -> Path:
    """
    Render a synthetic invoice/receipt-like PNG with controlled variation.

    The input invoice is the document-side claim. It can intentionally
    differ from the ledger record for evaluation scenarios.
    """
    if seed is not None:
        random.seed(seed)

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGB",
        (PAGE_WIDTH, PAGE_HEIGHT),
        color=(250, 249, 246),
    )

    draw = ImageDraw.Draw(image)

    title_font = load_font(46, bold=True)
    header_font = load_font(25, bold=True)
    body_font = load_font(23)
    small_font = load_font(19)
    total_font = load_font(31, bold=True)

    # Light visual variation: makes OCR and layout less trivial.
    line_color = random.choice(
        [
            (35, 35, 35),
            (45, 50, 60),
            (25, 45, 72),
        ]
    )

    accent_color = random.choice(
        [
            (35, 92, 145),
            (59, 103, 75),
            (115, 78, 137),
            (129, 79, 49),
        ]
    )

    vendor = str(invoice["vendor"])
    invoice_id = str(invoice["invoice_id"])
    invoice_date = str(invoice["invoice_date"])
    currency = str(invoice["currency"])
    fx_rate = float(invoice.get("fx_rate", 1.0))

    draw.rectangle(
        [0, 0, PAGE_WIDTH, 145],
        fill=accent_color,
    )

    draw.text(
        (MARGIN, 38),
        vendor,
        fill="white",
        font=title_font,
    )

    draw.text(
        (MARGIN, 205),
        "INVOICE",
        fill=line_color,
        font=title_font,
    )

    left_x = MARGIN
    right_x = 760
    metadata_y = 290

    metadata_rows = [
        ("Invoice No.", invoice_id),
        ("Invoice Date", invoice_date),
        ("Currency", currency),
        ("FX Rate", f"{fx_rate:.4f}"),
        ("Payment Terms", "Net 30"),
    ]

    for index, (label, value) in enumerate(metadata_rows):
        y = metadata_y + index * 48

        draw.text(
            (left_x, y),
            f"{label}:",
            fill=line_color,
            font=header_font,
        )

        draw.text(
            (right_x, y),
            str(value),
            fill=line_color,
            font=body_font,
        )

    table_top = 600

    draw.line(
        [(MARGIN, table_top), (PAGE_WIDTH - MARGIN, table_top)],
        fill=line_color,
        width=3,
    )

    columns = {
        "description": MARGIN + 10,
        "quantity": 720,
        "unit_price": 860,
        "amount": 1030,
    }

    for label, x in (
        ("Description", columns["description"]),
        ("Qty", columns["quantity"]),
        ("Unit Price", columns["unit_price"]),
        ("Line Total", columns["amount"]),
    ):
        draw.text(
            (x, table_top + 22),
            label,
            fill=line_color,
            font=header_font,
        )

    draw.line(
        [
            (MARGIN, table_top + 65),
            (PAGE_WIDTH - MARGIN, table_top + 65),
        ],
        fill=line_color,
        width=2,
    )

    line_items = build_line_items(invoice)

    current_y = table_top + 95
    subtotal = 0.0

    for line_item in line_items:
        quantity = int(line_item["quantity"])
        unit_price = float(line_item["unit_price"])
        line_total = round(quantity * unit_price * fx_rate, 2)

        subtotal += line_total

        draw.text(
            (columns["description"], current_y),
            str(line_item["description"])[:38],
            fill=line_color,
            font=body_font,
        )

        draw.text(
            (columns["quantity"], current_y),
            str(quantity),
            fill=line_color,
            font=body_font,
        )

        draw.text(
            (columns["unit_price"], current_y),
            money(unit_price, currency),
            fill=line_color,
            font=body_font,
        )

        draw.text(
            (columns["amount"], current_y),
            money(line_total, currency),
            fill=line_color,
            font=body_font,
        )

        current_y += 52

    summary_y = max(current_y + 100, 1120)
    document_total = float(invoice["amount"])

    totals = [
        ("Subtotal", subtotal),
        ("Tax", 0.00),
        ("TOTAL DUE", document_total),
    ]

    for label, value in totals:
        font = total_font if label == "TOTAL DUE" else body_font

        draw.text(
            (760, summary_y),
            label,
            fill=line_color,
            font=font,
        )

        draw.text(
            (1020, summary_y),
            money(value, currency),
            fill=line_color,
            font=font,
        )

        summary_y += 58

    footer_y = PAGE_HEIGHT - 180

    draw.line(
        [
            (MARGIN, footer_y - 25),
            (PAGE_WIDTH - MARGIN, footer_y - 25),
        ],
        fill=(150, 150, 150),
        width=1,
    )

    draw.text(
        (MARGIN, footer_y),
        "Please reference the invoice number with payment.",
        fill=(85, 85, 85),
        font=small_font,
    )

    draw.text(
        (MARGIN, footer_y + 35),
        "Generated by LedgerBridge AI synthetic evaluation suite.",
        fill=(110, 110, 110),
        font=small_font,
    )

    # Mild rotation + blur emulate a scan without making OCR unusable.
    rotation = random.choice(
        [-1.0, -0.5, 0.0, 0.5, 1.0]
    )

    image = image.rotate(
        rotation,
        resample=Image.Resampling.BICUBIC,
        fillcolor=(250, 249, 246),
    )

    if random.random() < 0.35:
        image = image.filter(
            ImageFilter.GaussianBlur(radius=0.25)
        )

    image.save(
        output_path,
        format="PNG",
        optimize=True,
    )

    return output_path