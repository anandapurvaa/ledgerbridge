# tests/synthetic/test_split_evaluation_manifest.py
from src.synthetic.split_evaluation_manifest import (
    stratified_split,
)


def test_stratified_split_preserves_scenarios():
    manifest = []

    for scenario in (
        "matched",
        "amount_mismatch",
        "fx_mismatch",
        "quantity_mismatch",
        "duplicate_charge",
    ):
        for index in range(10):
            manifest.append(
                {
                    "case_id": f"{scenario}-{index}",
                    "scenario": scenario,
                }
            )

    development, heldout = stratified_split(
        manifest,
        heldout_fraction=0.30,
        seed=42,
    )

    assert len(development) == 35
    assert len(heldout) == 15

    for scenario in (
        "matched",
        "amount_mismatch",
        "fx_mismatch",
        "quantity_mismatch",
        "duplicate_charge",
    ):
        assert sum(
            item["scenario"] == scenario
            for item in heldout
        ) == 3