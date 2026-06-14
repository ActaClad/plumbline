"""PLB-OUT-001 — LLM output parsed as JSON without error handling (taint rule)."""

from __future__ import annotations

from plumbline.rules.out.plb_out_001 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-OUT-001"
    assert RULE.category == "OUT"
    assert RULE.confidence.label == "High"


def test_guarded_parse_does_not_fire() -> None:
    assert run_file_rule(RULE, fixture_dir(RULE) / "good_guarded_parse.py") == []


def test_non_llm_json_does_not_fire() -> None:
    # json.loads on a file, not model output -> taint engine keeps it silent.
    assert run_file_rule(RULE, fixture_dir(RULE) / "good_not_llm_output.py") == []


def test_unguarded_parse_fires_once() -> None:
    findings = run_file_rule(RULE, fixture_dir(RULE) / "bad_unguarded_parse.py")
    assert len(findings) == 1
    assert "json.loads" in findings[0].message
