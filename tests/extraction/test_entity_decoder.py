# tests/extraction/test_entity_decoder.py
from src.extraction.entity_decoder import decode_bio_spans


def test_decoder_builds_bio_spans():
    spans = decode_bio_spans(
        words=[
            "ACME",
            "CLOUD",
            "DATE",
            "2026-08-23",
            "TOTAL",
            "123.45",
        ],
        labels=[
            "B-VENDOR",
            "I-VENDOR",
            "O",
            "B-DATE",
            "O",
            "B-TOTAL",
        ],
        scores=[0.95, 0.93, 0.99, 0.90, 0.98, 0.91],
    )

    assert len(spans) == 3
    assert spans[0].entity_type == "VENDOR"
    assert spans[0].text == "ACME CLOUD"
    assert spans[1].text == "2026-08-23"
    assert spans[2].text == "123.45"


def test_decoder_handles_invalid_i_tag_as_new_entity():
    spans = decode_bio_spans(
        words=["100.00", "200.00"],
        labels=["I-TOTAL", "I-TOTAL"],
        scores=[0.90, 0.92],
    )

    assert len(spans) == 1
    assert spans[0].entity_type == "TOTAL"
    assert spans[0].text == "100.00 200.00"