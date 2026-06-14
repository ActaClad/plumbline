"""PLB-EVAL-001 — no evaluation suite for LLM/agent code (project-scope)."""

from __future__ import annotations

from plumbline.rules.eval.plb_eval_001 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_project_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-EVAL-001"
    assert RULE.scope.value == "project"
    assert RULE.severity.label == "Major"
    assert RULE.confidence.label == "Medium"  # absence rule -> advisory


def test_a_test_not_touching_llm_paths_still_fires() -> None:
    # The knife-edge: bad_no_evals has a test_utils.py that tests an unrelated
    # helper. "A test exists" is not "the model is evaluated".
    fired = run_project_rule(RULE, fixture_dir(RULE) / "bad_no_evals")
    assert [f for f in fired if f.rule_id == RULE.id]


def test_finding_carries_scope_caveat() -> None:
    fired = run_project_rule(RULE, fixture_dir(RULE) / "bad_no_evals")
    msg = next(f.message for f in fired if f.rule_id == RULE.id)
    assert "scan the project root" in msg


def test_eval_framework_counts_as_a_suite() -> None:
    assert run_project_rule(RULE, fixture_dir(RULE) / "good_with_framework") == []


def test_package_dotted_import_is_recognized() -> None:
    # The realistic layout: tests/ doing `from myapp.agent import ...`. A miss
    # here would make EVAL-001 a false positive on well-tested package repos.
    assert run_project_rule(RULE, fixture_dir(RULE) / "good_package_layout") == []


def test_no_finding_without_agentic_code(tmp_path) -> None:
    (tmp_path / "plain.py").write_text("def add(a, b):\n    return a + b\n")
    assert run_project_rule(RULE, tmp_path) == []
