from src.extraction.sroie_preprocessor import (
    LABEL_TO_ID,
    assign_bio_labels,
    is_date_match,
    is_total_match,
    is_vendor_match,
    normalize_bbox,
    normalize_numeric,
    normalize_text,
    parse_date_to_iso,
)


def test_normalize_text_removes_receipt_punctuation():
    value = "BOOK TA .K(TAMAN DAYA) SDN BHD"

    assert normalize_text(value) == (
        "book ta k taman daya sdn bhd"
    )


def test_normalize_numeric_supports_multiple_formats():
    assert normalize_numeric("RM 9.00") == "9.00"
    assert normalize_numeric("1,234.56") == "1234.56"
    assert normalize_numeric("1.234,56") == "1234.56"


def test_parse_date_extracts_date_from_timestamp():
    assert parse_date_to_iso(
        "25/12/2018 8:13:39 PM"
    ) == "2018-12-25"

    assert parse_date_to_iso("25/12/2018") == "2018-12-25"
    assert parse_date_to_iso("2018-12-25") == "2018-12-25"


def test_date_match_handles_timestamp_vs_ground_truth():
    assert is_date_match(
        "25/12/2018 8:13:39 PM",
        "25/12/2018",
    )

def test_parse_date_supports_month_day_year_format():
    assert parse_date_to_iso("12/28/2017") == "2017-12-28"
    assert parse_date_to_iso("12/28/2017 10:17:32 PM") == (
        "2017-12-28"
    )


def test_parse_date_supports_month_name_formats():
    assert parse_date_to_iso("05 MAR 2018") == "2018-03-05"
    assert parse_date_to_iso("05 MAR 2018 18:24") == "2018-03-05"
    assert parse_date_to_iso("MAR 05, 2018") == "2018-03-05"


def test_date_match_handles_iso_ocr_and_us_ground_truth():
    assert is_date_match(
        "2017-12-28 22:17PM",
        "12/28/2017",
    )

def test_total_match_handles_currency_prefix():
    assert is_total_match("RM 9.00", "9.00")
    assert is_total_match("1.234,56", "1234.56")


def test_vendor_fuzzy_match_handles_ocr_typo():
    assert is_vendor_match(
        "BOOK TA .K(TAMAN DAYA) SDN BND",
        "BOOK TA .K (TAMAN DAYA) SDN BHD",
    )


def test_assign_bio_labels_for_company_date_and_total():
    words = [
        "ACME",
        "CLOUD",
        "SERVICES",
        "DATE:",
        "2026-08-23 08:00:00",
        "TOTAL:",
        "EUR 123.45",
    ]

    entities = {
        "company": "ACME CLOUD SERVICES",
        "date": "2026-08-23",
        "address": "",
        "total": "123.45",
    }

    labels = assign_bio_labels(words, entities)

    assert labels == [
        "B-VENDOR",
        "I-VENDOR",
        "I-VENDOR",
        "O",
        "B-DATE",
        "O",
        "B-TOTAL",
    ]


def test_normalize_bbox_maps_pixels_to_layoutlm_range():
    bbox = [50, 100, 450, 900]

    normalized = normalize_bbox(
        bbox=bbox,
        image_width=500,
        image_height=1000,
    )

    assert normalized == [100, 100, 900, 900]


def test_label_map_contains_required_labels():
    assert LABEL_TO_ID["O"] == 0
    assert "B-VENDOR" in LABEL_TO_ID
    assert "B-DATE" in LABEL_TO_ID
    assert "B-TOTAL" in LABEL_TO_ID

