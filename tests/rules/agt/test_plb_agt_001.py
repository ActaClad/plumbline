"""PLB-AGT-001 — agent loop without a max-iteration limit (one rule, 3 frameworks)."""

from __future__ import annotations

from plumbline.rules.agt.plb_agt_001 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-AGT-001"
    assert RULE.category == "AGT"
    assert RULE.severity.label == "Blocker"


def test_fires_on_all_three_frameworks_via_one_detector() -> None:
    # The DoD: the same detector flags LangChain, CrewAI, and a hand-rolled loop.
    d = fixture_dir(RULE)
    for bad in ("bad_langchain_uncapped.py", "bad_crewai_uncapped.py", "bad_handrolled_loop.py"):
        fired = [f for f in run_file_rule(RULE, d / bad) if f.rule_id == RULE.id]
        assert fired, f"expected AGT-001 to fire on {bad}"


def test_bare_framework_agent_does_not_fire() -> None:
    # Bare AgentExecutor is bounded by the framework default (ADR-0012 D4).
    fired = run_file_rule(RULE, fixture_dir(RULE) / "good_langchain_default.py")
    assert fired == []


def test_capped_handrolled_loop_does_not_fire() -> None:
    fired = run_file_rule(RULE, fixture_dir(RULE) / "good_handrolled_capped.py")
    assert fired == []
