# src/extraction/run_extraction_demo.py
import json
from pathlib import Path

from src.extraction.extraction_service import (
    extract_invoice_from_image,
)


SAMPLE_IMAGE = Path("data/raw/sroie_samples/sample_000.png")


def main() -> None:
    if not SAMPLE_IMAGE.exists():
        raise FileNotFoundError(
            f"Sample image not found: {SAMPLE_IMAGE}\n"
            "Run `python -m src.data.inspect_sroie_dataset` first."
        )

    result = extract_invoice_from_image(SAMPLE_IMAGE)

    print("\nExtracted invoice fields:")
    print(
        json.dumps(
            result["extracted_fields"],
            indent=2,
            ensure_ascii=False,
        )
    )

    print("\nOCR summary:")
    print(f"Word count: {len(result['ocr_result']['words'])}")
    print(
        "Mean confidence: "
        f"{result['ocr_result']['mean_confidence']}"
    )

    print("\nOCR lines:")
    for line in result["ocr_result"]["lines"][:20]:
        print(f"  {line}")


if __name__ == "__main__":
    main()