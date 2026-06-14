"""PLB-MDL-001 — hardcoded model name scattered across modules (project-scope)."""

from __future__ import annotations

from plumbline.rules.base import RuleScope
from plumbline.rules.mdl.plb_mdl_001 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_project_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata_and_scope() -> None:
    assert RULE.id == "PLB-MDL-001"
    assert RULE.scope is RuleScope.PROJECT
    assert RULE.confidence.label == "Medium"


def test_scattered_flags_each_occurrence() -> None:
    findings = run_project_rule(RULE, fixture_dir(RULE) / "bad_scattered")
    assert len(findings) == 2  # one per module
    files = {f.file for f in findings}
    assert files == {"summarizer.py", "classifier.py"}


def test_centralized_is_silent() -> None:
    assert run_project_rule(RULE, fixture_dir(RULE) / "good_centralized") == []


def test_single_module_is_silent() -> None:
    assert run_project_rule(RULE, fixture_dir(RULE) / "good_single_module") == []
