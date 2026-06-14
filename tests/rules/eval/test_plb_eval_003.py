"""PLB-EVAL-003 — CI exists but runs no evals (project-scope, grep rule)."""

from __future__ import annotations

from plumbline.rules.eval.plb_eval_003 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_project_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-EVAL-003"
    assert RULE.scope.value == "project"
    assert RULE.confidence.label == "Medium"
    assert RULE.grep_rule is True  # sanctioned pattern rule (ADR-0013 D2)


def test_ci_running_pytest_is_silent() -> None:
    assert run_project_rule(RULE, fixture_dir(RULE) / "good_ci_runs_tests") == []


def test_no_ci_is_silent_not_eval001_territory() -> None:
    # With no CI at all there is nothing to gate; EVAL-001 covers "no evals".
    assert run_project_rule(RULE, fixture_dir(RULE) / "good_no_ci") == []


def test_ci_without_eval_token_fires_with_caveat() -> None:
    fired = run_project_rule(RULE, fixture_dir(RULE) / "bad_ci_no_evals")
    msg = next(f.message for f in fired if f.rule_id == RULE.id)
    assert "CI pipeline but it never runs" in msg
    assert "scan the project root" in msg
