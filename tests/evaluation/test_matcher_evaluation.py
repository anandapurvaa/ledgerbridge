# tests/evaluation/test_matcher_evaluation.py
from src.data.generate_evaluation_cases import generate_cases
from src.evaluation.evaluate_matcher import evaluate_cases


def test_generator_creates_balanced_scenarios():
    cases = generate_cases(records_per_scenario=3, seed=42)

    assert len(cases) == 15

    statuses = [case["expected_status"] for case in cases]

    assert statuses.count("matched") == 3
    assert statuses.count("fx_mismatch") == 3
    assert statuses.count("quantity_mismatch") == 3
    assert statuses.count("amount_mismatch") == 3
    assert statuses.count("duplicate_charge") == 3


def test_financial_control_baseline_meets_threshold():
    cases = generate_cases(records_per_scenario=3, seed=42)
    report = evaluate_cases(cases)

    assert report["summary"]["total_cases"] == 15

    # Current controlled baseline should robustly exceed this.
    assert report["summary"]["accuracy"] >= 0.85

    predictions = {
        case["predicted_status"]
        for case in report["case_results"]
    }

    assert "matched" in predictions
    assert "fx_mismatch" in predictions
    assert "quantity_mismatch" in predictions
    assert "amount_mismatch" in predictions