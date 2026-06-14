"""PLB-RES-005 — bare/broad except swallowing an LLM call."""

from __future__ import annotations

from plumbline.rules.res.plb_res_005 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-RES-005"
    assert RULE.severity.label == "Critical"
    assert RULE.confidence.label == "High"


def test_logging_handler_does_not_fire() -> None:
    assert run_file_rule(RULE, fixture_dir(RULE) / "good_logs_and_returns.py") == []


def test_reraise_does_not_fire() -> None:
    assert run_file_rule(RULE, fixture_dir(RULE) / "good_specific_reraise.py") == []


def test_anchors_at_the_handler() -> None:
    findings = run_file_rule(RULE, fixture_dir(RULE) / "bad_broad_except_pass.py")
    assert len(findings) == 1
    assert "swallows" in findings[0].message
