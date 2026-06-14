"""PLB-RES-005 — Bare/broad except swallowing an LLM call.

`try: ... except: pass` (or `except Exception: pass`) around a model call hides
failures: the call fails, nothing is logged or re-raised, and downstream code
runs on corrupt/empty state. Detection is precise — it fires only when the
handler body is exactly `pass`/`...` (genuinely swallowing), not on handlers
that log, re-raise, or return an explicit error.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, SemanticTag, Severity
from .._ast_helpers import enclosing_try_body
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Catch specific exceptions, log them, and return an explicit error — never swallow.

Bad:
    try:
        resp = client.chat.completions.create(...)
    except Exception:
        pass

Good:
    try:
        resp = client.chat.completions.create(...)
    except (APIError, APITimeoutError) as exc:
        logger.error("LLM call failed: %s", exc)
        return ErrorResult(exc)
"""

_BROAD_NAMES = frozenset({"Exception", "BaseException"})


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    seen: set[int] = set()
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        try_node = enclosing_try_body(ctx.tree, sn.node)
        if try_node is None:
            continue
        for handler in try_node.handlers:
            if id(handler) in seen or not _is_broad(handler) or not _swallows(handler.body):
                continue
            seen.add(id(handler))
            findings.append(
                ctx.finding(
                    handler,
                    "LLM call is wrapped in a bare/broad except that swallows the error "
                    "(no logging, no re-raise); failures pass silently to downstream code.",
                )
            )
    return findings


def _is_broad(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:  # bare `except:`
        return True
    return isinstance(handler.type, ast.Name) and handler.type.id in _BROAD_NAMES


def _swallows(body: list[ast.stmt]) -> bool:
    """True if the handler body does nothing but `pass` / `...` (a docstring ok) —
    i.e. it neither logs, re-raises, nor returns an explicit result."""
    real = [s for s in body if not _is_ellipsis_or_doc(s)]
    return all(isinstance(s, ast.Pass) for s in real)


def _is_ellipsis_or_doc(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and (stmt.value.value is Ellipsis or isinstance(stmt.value.value, str))
    )


RULE = Rule(
    id="PLB-RES-005",
    title="Bare except swallowing LLM errors",
    category="RES",
    pillar=Pillar.RELIABILITY,
    severity=Severity.CRITICAL,
    confidence=Confidence.HIGH,
    why_it_matters=(
        "`except: pass` around a model call hides failures and corrupts downstream state."
    ),
    remediation=REMEDIATION,
    detect=detect,
)
