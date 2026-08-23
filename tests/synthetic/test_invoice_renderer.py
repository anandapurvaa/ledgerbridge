# tests/synthetic/test_invoice_renderer.py
from pathlib import Path

from PIL import Image

from src.synthetic.invoice_renderer import render_invoice


def test_renderer_creates_openable_invoice_png(tmp_path: Path):
    invoice = {
        "invoice_id": "LB-INV-00001",
        "invoice_date": "2026-08-23",
        "vendor": "Acme Cloud Services",
        "amount": 1234.56,
        "currency": "EUR",
        "quantity": 4,
        "fx_rate": 1.0,
        "line_items": [
            {
                "description": "Cloud support",
                "qty": 4,
                "price": 308.64,
            }
        ],
    }

    image_path = tmp_path / "invoice.png"

    output_path = render_invoice(
        invoice=invoice,
        output_path=image_path,
        seed=42,
    )

    assert output_path.exists()

    with Image.open(output_path) as image:
        assert image.mode == "RGB"
        assert image.width > 500
        assert image.height > 500