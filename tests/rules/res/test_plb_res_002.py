"""PLB-RES-002 — retries disabled on an LLM call."""

from __future__ import annotations

from plumbline.rules.res.plb_res_002 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-RES-002"
    assert RULE.severity.label == "Critical"
    assert RULE.confidence.label == "High"


def test_default_retries_do_not_fire() -> None:
    assert run_file_rule(RULE, fixture_dir(RULE) / "good_default_retries.py") == []


def test_message_names_max_retries() -> None:
    findings = run_file_rule(RULE, fixture_dir(RULE) / "bad_call_no_retries.py")
    assert len(findings) == 1
    assert "max_retries=0" in findings[0].message
