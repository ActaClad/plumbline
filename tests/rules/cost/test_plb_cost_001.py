"""PLB-COST-001 — no max_tokens / output cap."""

from __future__ import annotations

from plumbline.rules.cost.plb_cost_001 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-COST-001"
    assert RULE.category == "COST"
    assert RULE.severity.label == "Major"  # advisory in the default gate
    assert RULE.confidence.label == "High"


def test_unknown_kwargs_stays_silent(tmp_path: object) -> None:
    assert run_file_rule(RULE, fixture_dir(RULE) / "good_unknown_kwargs.py") == []
