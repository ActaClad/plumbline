"""PLB-MDL-007 — Anthropic extended-thinking budget misconfigured.

Anthropic extended thinking imposes hard constraints on `budget_tokens`:
it must be **>= 1024** and **strictly less than `max_tokens`**. Violating either
returns an HTTP 400 on every call — a config that looks plausible in code but
never runs.

Detection is a pure literal comparison over the call's `thinking={...}` dict and
`max_tokens` keyword — it fires only when both values are **provable integer
literals** (a budget passed via a variable is not flagged; precision over recall).
The `thinking=` dict shape is Anthropic-specific, so no separate provider gate is
needed. Ships **Medium/advisory** until a `/benchmark` precision pass (ADR-0018).
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

_MIN_BUDGET = 1024

REMEDIATION = """\
Anthropic extended thinking requires `budget_tokens >= 1024` AND
`budget_tokens < max_tokens`. Otherwise the call returns HTTP 400.

Bad:
    client.messages.create(model="claude-sonnet-4-5", max_tokens=8000,
        thinking={"type": "enabled", "budget_tokens": 16000}, ...)   # budget >= max_tokens -> 400

Good:
    client.messages.create(model="claude-sonnet-4-5", max_tokens=16000,
        thinking={"type": "enabled", "budget_tokens": 8000}, ...)
"""


def _keyword_value(node: ast.AST, name: str) -> ast.expr | None:
    if not isinstance(node, ast.Call):
        return None
    for kw in node.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _int_literal(expr: ast.expr | None) -> int | None:
    # bool is an int subclass — exclude it so `budget_tokens=True` isn't read as 1.
    if (
        isinstance(expr, ast.Constant)
        and isinstance(expr.value, int)
        and not isinstance(expr.value, bool)
    ):
        return expr.value
    return None


def _dict_int(d: ast.Dict, key: str) -> int | None:
    for k, v in zip(d.keys, d.values, strict=False):
        if isinstance(k, ast.Constant) and k.value == key:
            return _int_literal(v)
    return None


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        thinking = _keyword_value(sn.node, "thinking")
        if not isinstance(thinking, ast.Dict):
            continue
        budget = _dict_int(thinking, "budget_tokens")
        if budget is None:
            continue  # not a provable literal — do not guess (no FP)
        max_tokens = _int_literal(_keyword_value(sn.node, "max_tokens"))
        if budget < _MIN_BUDGET:
            findings.append(
                ctx.finding(
                    sn.node,
                    f"Extended-thinking budget_tokens={budget} is below the 1024 minimum; "
                    "Anthropic rejects it with HTTP 400 on every call.",
                )
            )
        elif max_tokens is not None and budget >= max_tokens:
            findings.append(
                ctx.finding(
                    sn.node,
                    f"Extended-thinking budget_tokens={budget} must be strictly less than "
                    f"max_tokens={max_tokens}; Anthropic rejects budget >= max_tokens with "
                    "HTTP 400 on every call.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-MDL-007",
    title="Anthropic extended-thinking budget misconfigured",
    category="MDL",
    pillar=Pillar.RELIABILITY,
    severity=Severity.CRITICAL,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "An out-of-range thinking budget is a guaranteed HTTP 400 — the call fails "
        "on every invocation, not intermittently."
    ),
    standards=("CWE-628", "CWE-1284", "OWASP-LLM10"),
    remediation=REMEDIATION,
    detect=detect,
)
