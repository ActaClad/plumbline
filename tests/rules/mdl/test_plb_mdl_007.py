"""PLB-MDL-007 — Anthropic extended-thinking budget misconfigured."""

from __future__ import annotations

from plumbline.rules.mdl.plb_mdl_007 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-MDL-007"
    assert RULE.severity.label == "Critical"
    assert RULE.confidence.label == "Medium"  # advisory until benchmarked (ADR-0018)
    assert "CWE-1284" in RULE.standards


def test_budget_below_minimum_message() -> None:
    d = fixture_dir(RULE)
    fired = [f for f in run_file_rule(RULE, d / "bad_budget_too_small.py") if f.rule_id == RULE.id]
    assert fired and "below the 1024 minimum" in fired[0].message


def test_budget_ge_maxtokens_message() -> None:
    d = fixture_dir(RULE)
    fired = [
        f for f in run_file_rule(RULE, d / "bad_budget_ge_maxtokens.py") if f.rule_id == RULE.id
    ]
    assert fired and "strictly less than" in fired[0].message


def test_dynamic_budget_is_silent() -> None:
    # A non-literal budget can't be proven wrong — no false positive.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_budget_dynamic.py") == []
