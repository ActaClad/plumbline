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
from plumbline.core.derive import derive_semantics
from plumbline.core.taint import analyze_taint
from plumbline.model import Finding, assign_fingerprints
from plumbline.rules.base import (
    AnalysisContext,
    FileAnalysis,
    ProjectContext,
    Rule,
    RuleScope,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures"


def _file_analysis(rel: str, source: str) -> FileAnalysis:
    tree = parse(rel, source)
    collected = collect_semantics(tree, ADAPTERS)
    collected.extend(derive_semantics(tree, collected))  # AGENT_LOOP (ADR-0012)
    semantics = SemanticIndex(collected)
    taint = analyze_taint(tree, semantics)
    return FileAnalysis(file=rel, tree=tree, semantics=semantics, taint=taint)


def run_file_rule(rule: Rule, path: Path) -> list[Finding]:
    """Run a FILE-scope rule against one source file; return its findings."""
    analysis = _file_analysis(path.name, path.read_text(encoding="utf-8"))
    ctx = AnalysisContext(analysis, rule, Config())
    return assign_fingerprints(list(rule.detect(ctx)))


def run_project_rule(rule: Rule, root: Path) -> list[Finding]:
    """Run a PROJECT-scope rule against a directory (mini-repo); return findings."""
    analyses = [
        _file_analysis(p.relative_to(root).as_posix(), p.read_text(encoding="utf-8"))
        for p in sorted(root.rglob("*.py"))
    ]
    ctx = ProjectContext(analyses, rule, Config())
    return assign_fingerprints(list(rule.detect(ctx)))


def fixture_dir(rule: Rule) -> Path:
    return FIXTURES / rule.id


def assert_fixtures(rule: Rule) -> None:
    """Assert the rule has >=1 bad and >=1 good fixture, and that they behave.

    FILE-scope rules use `bad_*.py` / `good_*.py` files; PROJECT-scope rules use
    `bad_*/` / `good_*/` directories (mini-repos, ADR-0010 D3).
    """
    d = fixture_dir(rule)
    if rule.scope is RuleScope.PROJECT:
        bad = sorted(p for p in d.glob("bad_*") if p.is_dir())
        good = sorted(p for p in d.glob("good_*") if p.is_dir())
        runner = run_project_rule
    else:
        bad = sorted(d.glob("bad_*.py"))
        good = sorted(d.glob("good_*.py"))
        runner = run_file_rule
    assert bad, f"{rule.id}: needs at least one bad fixture under fixtures/{rule.id}/"
    assert good, f"{rule.id}: needs at least one good fixture under fixtures/{rule.id}/"
    for path in bad:
        fired = [f for f in runner(rule, path) if f.rule_id == rule.id]
        assert fired, f"{rule.id}: expected a finding on {path.name}, got none"
    for path in good:
        fired = [f for f in runner(rule, path) if f.rule_id == rule.id]
        assert not fired, f"{rule.id}: false positive on {path.name}: {fired}"
