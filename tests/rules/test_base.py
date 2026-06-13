"""Tests for the rule contract, contexts, and discovery (ADR-0005, ADR-0010)."""

from __future__ import annotations

import ast

import pytest

from plumbline.adapters.base import SemanticIndex
from plumbline.config import Config, RulesConfig
from plumbline.core.ast_layer import parse
from plumbline.core.taint import TaintView
from plumbline.model import Confidence, FindingDraft, Pillar, Severity
from plumbline.rules.base import (
    AnalysisContext,
    FileAnalysis,
    Rule,
    RuleLoadError,
    RuleScope,
    _validate,
    discover_rules,
)


def _rule(rule_id: str = "PLB-RES-001", **kw: object) -> Rule:
    base: dict[str, object] = {
        "id": rule_id,
        "title": "LLM call without timeout",
        "category": rule_id.split("-")[1],
        "pillar": Pillar.RELIABILITY,
        "severity": Severity.BLOCKER,
        "confidence": Confidence.HIGH,
        "why_it_matters": "It can hang the worker pool.",
        "remediation": "Set a timeout.",
        "detect": lambda ctx: [],
    }
    base.update(kw)
    return Rule(**base)  # type: ignore[arg-type]


def _ctx(src: str, rule: Rule, config: Config | None = None) -> AnalysisContext:
    st = parse("app/agent.py", src)
    analysis = FileAnalysis(
        file="app/agent.py", tree=st, semantics=SemanticIndex([]), taint=TaintView({}, {})
    )
    return AnalysisContext(analysis, rule, config or Config())


# --- discovery ----------------------------------------------------------------


def test_discover_rules_finds_res_001() -> None:
    # Discovery returns a sorted, validated list; PLB-RES-001 is the first rule.
    ids = [r.id for r in discover_rules()]
    assert "PLB-RES-001" in ids
    assert ids == sorted(ids)


# --- validation (ADR-0005 D2) -------------------------------------------------


def test_validate_accepts_well_formed_rule() -> None:
    _validate(_rule(), "plumbline.rules.res.plb_res_001")  # no raise


def test_validate_rejects_malformed_id() -> None:
    with pytest.raises(RuleLoadError, match="malformed rule id"):
        _validate(_rule("RES-1"), "plumbline.rules.res.res_1")


def test_validate_rejects_unknown_category() -> None:
    with pytest.raises(RuleLoadError, match="unknown category 'ZZZ'"):
        _validate(_rule("PLB-ZZZ-001"), "plumbline.rules.zzz.plb_zzz_001")


def test_validate_rejects_module_name_mismatch() -> None:
    with pytest.raises(RuleLoadError, match="must live in a module named 'plb_res_001'"):
        _validate(_rule("PLB-RES-001"), "plumbline.rules.res.something_else")


def test_validate_rejects_category_field_mismatch() -> None:
    with pytest.raises(RuleLoadError, match="!= id category"):
        _validate(_rule("PLB-RES-001", category="SEC"), "plumbline.rules.res.plb_res_001")


def test_validate_rejects_empty_metadata() -> None:
    with pytest.raises(RuleLoadError, match="must be non-empty"):
        _validate(_rule(why_it_matters="  "), "plumbline.rules.res.plb_res_001")


# --- finding builder (ADR-0002 D1) --------------------------------------------


def test_finding_builder_fills_metadata_and_location() -> None:
    rule = _rule()
    ctx = _ctx("def f():\n    y = client.create(model='m')\n", rule)
    call = next(n for n in ast.walk(ctx.tree.tree) if isinstance(n, ast.Call))
    draft = ctx.finding(call, "no timeout on this call")
    assert isinstance(draft, FindingDraft)
    assert draft.rule_id == "PLB-RES-001"
    assert draft.message == "no timeout on this call"
    assert draft.why_it_matters == "It can hang the worker pool."
    assert draft.file == "app/agent.py"
    assert draft.line == 2
    assert draft.severity is Severity.BLOCKER
    assert draft.anchor == "y = client.create(model='m')"
    assert draft.snippet == "client.create(model='m')"


def test_finding_builder_applies_config_severity_override() -> None:
    rule = _rule()
    config = Config(rules=RulesConfig(severity_override={"PLB-RES-001": Severity.MINOR}))
    ctx = _ctx("x = client.create()\n", rule, config)
    call = next(n for n in ast.walk(ctx.tree.tree) if isinstance(n, ast.Call))
    draft = ctx.finding(call, "msg")
    assert draft.severity is Severity.MINOR  # overridden
    assert draft.confidence is Confidence.HIGH  # unchanged


def test_finding_builder_explicit_override_beats_config() -> None:
    rule = _rule()
    ctx = _ctx("x = client.create()\n", rule)
    call = next(n for n in ast.walk(ctx.tree.tree) if isinstance(n, ast.Call))
    draft = ctx.finding(call, "msg", severity=Severity.CRITICAL)
    assert draft.severity is Severity.CRITICAL


def test_rule_defaults_to_file_scope() -> None:
    assert _rule().scope is RuleScope.FILE
