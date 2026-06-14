"""PLB-AGT-002 — no termination condition in a custom agent loop."""

from __future__ import annotations

from plumbline.rules.agt.plb_agt_002 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-AGT-002"
    assert RULE.severity.label == "Critical"


def test_goal_break_loop_does_not_fire() -> None:
    # A while True with a reachable goal exit terminates — distinct from AGT-001.
    assert run_file_rule(RULE, fixture_dir(RULE) / "good_goal_break.py") == []


def test_for_loop_does_not_fire() -> None:
    assert run_file_rule(RULE, fixture_dir(RULE) / "good_for_loop.py") == []
