"""PLB-MDL-001 — Hardcoded model name scattered across modules (project-scope).

When the same model identifier is written as an inline string literal at call
sites in two or more modules, swapping models becomes an error-prone find-and-
replace and behavior drift is untraceable. Centralizing the model id in one
config value fixes both. This is a PROJECT-scope rule (ADR-0010): it needs to see
the whole repo to know a literal is *scattered* rather than defined once.

Medium confidence: inlining the same model in multiple files is a strong
maturity signal but not always a defect (a small script legitimately may), so it
advises rather than gates.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, SemanticTag, Severity
from ..base import ProjectContext, Rule, RuleScope

REMEDIATION = """\
Centralize the model id in one config value; reference it everywhere.

Bad (scattered literals across modules):
    # summarizer.py
    client.chat.completions.create(model="gpt-4o", ...)
    # classifier.py
    client.chat.completions.create(model="gpt-4o", ...)

Good (one source of truth):
    # config.py
    CHAT_MODEL = "gpt-4o"
    # everywhere else
    client.chat.completions.create(model=settings.CHAT_MODEL, ...)
"""


def detect(ctx: ProjectContext) -> list[FindingDraft]:
    # model literal -> list of (file, literal-node)
    occurrences: dict[str, list[tuple[str, ast.AST]]] = {}
    for fa in ctx.files:
        for sn in fa.semantics.by_tag(SemanticTag.LLM_CALL):
            literal = _model_literal(sn.node)
            if literal is not None:
                value, node = literal
                occurrences.setdefault(value, []).append((fa.file, node))

    findings: list[FindingDraft] = []
    for model, sites in sorted(occurrences.items()):
        files = {file for file, _ in sites}
        if len(files) < 2:
            continue  # a single module is allowed to define it
        for file, node in sites:
            findings.append(
                ctx.finding(
                    file,
                    node,
                    f"Model {model!r} is hardcoded as a string literal in "
                    f"{len(files)} modules; centralize it in one config value.",
                )
            )
    return findings


def _model_literal(call: ast.AST) -> tuple[str, ast.AST] | None:
    if not isinstance(call, ast.Call):
        return None
    for kw in call.keywords:
        if (
            kw.arg == "model"
            and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str)
        ):
            return kw.value.value, kw.value
    return None


RULE = Rule(
    id="PLB-MDL-001",
    title="Hardcoded / unpinned model name",
    category="MDL",
    pillar=Pillar.RELIABILITY,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "Scattered model-name literals make swaps error-prone and behavior drift untraceable."
    ),
    remediation=REMEDIATION,
    detect=detect,
    scope=RuleScope.PROJECT,
)
