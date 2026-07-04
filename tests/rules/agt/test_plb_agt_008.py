"""PLB-AGT-008 — AutoGen team with no turn cap or termination condition."""

from __future__ import annotations

from plumbline.rules.agt.plb_agt_008 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-AGT-008"
    assert RULE.category == "AGT"
    assert RULE.confidence.label == "Medium"
    assert "CWE-835" in RULE.standards


def test_message_names_the_team() -> None:
    d = fixture_dir(RULE)
    fired = [f for f in run_file_rule(RULE, d / "bad_no_bound.py") if f.rule_id == RULE.id]
    assert fired and "RoundRobinGroupChat" in fired[0].message


def test_import_gate_silences_unrelated_class() -> None:
    # Same class name from a non-AutoGen library must not fire (precision boundary).
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_not_autogen.py") == []
