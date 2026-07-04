"""PLB-RES-010 — streamed response not used as a context manager."""

from __future__ import annotations

from plumbline.rules.res.plb_res_010 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-RES-010"
    assert RULE.category == "RES"
    assert RULE.severity.label == "Major"
    assert RULE.confidence.label == "Medium"  # advisory until benchmarked


def test_with_statement_is_silent() -> None:
    # The whole point: correct context-manager use must never fire.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_stream_with.py") == []
    assert run_file_rule(RULE, d / "good_openai_responses_stream_with.py") == []


def test_assigned_stream_fires() -> None:
    d = fixture_dir(RULE)
    fired = [f for f in run_file_rule(RULE, d / "bad_stream_assigned.py") if f.rule_id == RULE.id]
    assert fired
    assert "context manager" in fired[0].message
