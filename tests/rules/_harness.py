"""Shared rule-test harness.

Runs a single rule against its `fixtures/<RULE_ID>/` files and asserts the
contract: every `bad_*` fires, every `good_*` stays silent (CLAUDE.md §1.5,
rule-plugin-contract §3). Used by per-rule tests and the fixtures meta-test.
"""

from __future__ import annotations

from pathlib import Path

from plumbline.adapters import ADAPTERS
from plumbline.adapters.base import SemanticIndex, collect_semantics
from plumbline.config import Config
from plumbline.core.ast_layer import parse
from plumbline.core.taint import analyze_taint
from plumbline.model import Finding, assign_fingerprints
from plumbline.rules.base import AnalysisContext, FileAnalysis, Rule, RuleScope

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures"


def run_file_rule(rule: Rule, path: Path) -> list[Finding]:
    """Run a FILE-scope rule against one source file; return its findings."""
    src = path.read_text(encoding="utf-8")
    tree = parse(path.name, src)
    semantics = SemanticIndex(collect_semantics(tree, ADAPTERS))
    taint = analyze_taint(tree, semantics)
    analysis = FileAnalysis(file=path.name, tree=tree, semantics=semantics, taint=taint)
    ctx = AnalysisContext(analysis, rule, Config())
    return assign_fingerprints(list(rule.detect(ctx)))


def fixture_dir(rule: Rule) -> Path:
    return FIXTURES / rule.id


def assert_fixtures(rule: Rule) -> None:
    """Assert the rule has >=1 bad and >=1 good fixture, and that they behave.

    File-scope only in M1; project-scope (directory fixtures, ADR-0010 D3) is
    added in M3.
    """
    if rule.scope is not RuleScope.FILE:
        return
    d = fixture_dir(rule)
    bad = sorted(d.glob("bad_*.py"))
    good = sorted(d.glob("good_*.py"))
    assert bad, f"{rule.id}: needs at least one fixtures/{rule.id}/bad_*.py"
    assert good, f"{rule.id}: needs at least one fixtures/{rule.id}/good_*.py"
    for path in bad:
        fired = [f for f in run_file_rule(rule, path) if f.rule_id == rule.id]
        assert fired, f"{rule.id}: expected a finding on {path.name}, got none"
    for path in good:
        fired = [f for f in run_file_rule(rule, path) if f.rule_id == rule.id]
        assert not fired, f"{rule.id}: false positive on {path.name}: {fired}"
