"""PLB-EVAL-001 — No evaluation suite for LLM/agent code (project-scope).

The defining harness-engineering defect: a repo ships LLM/agent behavior with no
way to tell when it regresses. This is a project-scope absence rule (ADR-0010) —
it fires once when the project has agentic code but no detectable evaluation
suite. The knife-edge (spec §EVAL-001): an "eval suite" means *a test that
exercises the LLM paths* or an LLM-eval framework — not merely that some unrelated
test file exists. Ships Medium: detection recall is the precision ceiling, and a
mis-scoped scan (`./src` only) can't see `tests/`, so it advises, never gates.
"""

from __future__ import annotations

from ...model import Confidence, FindingDraft, Pillar, Severity
from .._harness_evidence import (
    SCOPE_CAVEAT,
    agentic_anchor,
    agentic_module_names,
    imported_modules,
    is_test_file,
)
from ..base import ProjectContext, Rule, RuleScope

REMEDIATION = """\
Add an evaluation suite that exercises the model paths with reference outputs.

- A test that imports your agent/LLM module and asserts on its behavior, or
- an LLM-eval framework (deepeval, ragas, langsmith eval, inspect_ai, …) with a
  golden dataset and regression thresholds.

Gate model/prompt changes on the suite so behavior regressions are caught before
they ship — this is the difference between shipping blind and shipping verified.
"""

# Eval-specific framework roots (NOT "langchain" — too broad to mean "eval").
_EVAL_ROOTS = frozenset(
    {"deepeval", "ragas", "trulens", "trulens_eval", "inspect_ai", "braintrust", "promptfoo"}
)


def detect(ctx: ProjectContext) -> list[FindingDraft]:
    anchor = agentic_anchor(ctx.files)
    if anchor is None:
        return []  # no LLM/agent code -> rule is N/A
    if _has_eval_evidence(ctx):
        return []
    file, node = anchor
    return [
        ctx.finding(
            file,
            node,
            "This project ships LLM/agent code with no detectable evaluation suite; "
            "model/prompt changes go out unverified." + SCOPE_CAVEAT,
        )
    ]


def _has_eval_evidence(ctx: ProjectContext) -> bool:
    llm_modules = agentic_module_names(ctx.files)
    for fa in ctx.files:
        modules = imported_modules(fa)
        if any(_is_eval_import(m) for m in modules):
            return True
        if is_test_file(fa.file) and _imports_agentic(modules, llm_modules):
            return True
    return False


def _is_eval_import(module: str) -> bool:
    root = module.split(".")[0]
    return root in _EVAL_ROOTS or "evaluation" in module or "evals" in module


def _imports_agentic(modules: set[str], llm_modules: set[str]) -> bool:
    return any(m in llm_modules or m.split(".")[-1] in llm_modules for m in modules)


RULE = Rule(
    id="PLB-EVAL-001",
    title="No evaluation suite for LLM/agent code",
    category="EVAL",
    pillar=Pillar.HARNESS,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "LLM/agent code with no eval suite ships behavior changes blind — regressions reach prod."
    ),
    standards=("NIST-AI-RMF:MEASURE",),
    remediation=REMEDIATION,
    detect=detect,
    scope=RuleScope.PROJECT,
)
