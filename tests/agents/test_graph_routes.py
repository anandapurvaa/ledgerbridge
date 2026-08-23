from src.agents.graph_routes import (
    route_after_duplicate_detection,
    route_after_extractor,
)


def complete_extracted_fields() -> dict:
    return {
        "invoice_id": "LB-INV-00001",
        "invoice_date": "2026-01-10",
        "vendor": "Acme Cloud Services",
        "amount": 100.0,
        "currency": "EUR",
        "quantity": 1,
        "fx_rate": 1.0,
    }


def test_complete_extraction_routes_to_ledger_query():
    state = {
        "extracted_fields": complete_extracted_fields(),
    }

    assert route_after_extractor(state) == "query_ledger"


def test_empty_extraction_routes_to_investigator():
    state = {
        "extracted_fields": {},
    }

    assert route_after_extractor(state) == "investigator"


def test_incomplete_extraction_routes_to_investigator():
    state = {
        "extracted_fields": {
            "invoice_id": "LB-INV-00001",
            "vendor": "Acme Cloud Services",
        },
    }

    assert route_after_extractor(state) == "investigator"


def test_matched_result_routes_to_audit_writer():
    state = {
        "reconciliation_result": {
            "status": "matched",
        },
    }

    assert route_after_duplicate_detection(state) == (
        "write_audit"
    )


def test_amount_mismatch_routes_to_investigator():
    state = {
        "reconciliation_result": {
            "status": "amount_mismatch",
        },
    }

    assert route_after_duplicate_detection(state) == (
        "investigator"
    )


def test_duplicate_charge_routes_to_investigator():
    state = {
        "reconciliation_result": {
            "status": "duplicate_charge",
        },
    }

    assert route_after_duplicate_detection(state) == (
        "investigator"
    )


def test_missing_result_defaults_to_investigator():
    assert route_after_duplicate_detection({}) == (
        "investigator"
    )