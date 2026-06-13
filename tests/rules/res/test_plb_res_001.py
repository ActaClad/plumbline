"""PLB-RES-001 — LLM/tool call without timeout."""

from __future__ import annotations

from plumbline.rules.res.plb_res_001 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-RES-001"
    assert RULE.category == "RES"
    assert RULE.severity.label == "Blocker"
    # Medium until /benchmark measures precision (CLAUDE.md §1.3); -> High in M3.
    assert RULE.confidence.label == "Medium"


def test_message_names_the_disabled_timeout() -> None:
    findings = run_file_rule(RULE, fixture_dir(RULE) / "bad_call_timeout_disabled.py")
    assert len(findings) == 1
    assert "timeout=None" in findings[0].message
    assert findings[0].snippet is not None and "create" in findings[0].snippet


def test_client_level_disable_also_fires() -> None:
    findings = run_file_rule(RULE, fixture_dir(RULE) / "bad_client_timeout_disabled.py")
    assert len(findings) == 1


def test_sdk_default_does_not_fire() -> None:
    findings = run_file_rule(RULE, fixture_dir(RULE) / "good_sdk_default.py")
    assert findings == []
