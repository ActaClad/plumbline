"""PLB-RES-010 — Streamed response not used as a context manager (leak).

The OpenAI/Anthropic streaming helpers — `client.messages.stream(...)`,
`client.responses.stream(...)`, `client.chat.completions.stream(...)` — return a
**context manager** that cancels the request and releases the HTTP connection on
exit. Used any other way (`s = client.messages.stream(...)`, or iterated
directly), the connection is never guaranteed to close: under load this exhausts
the client's connection pool and hangs workers.

Detection is tightly scoped to those `.stream()` helper calls (the SDK must be
imported in-file, ADR-0016) and fires only when the call is **not** the context
expression of a `with`/`async with`. That tight scope keeps precision high; it
does NOT touch `create(..., stream=True)`, whose iterate-to-completion pattern is
often legitimate. Ships **Medium/advisory** until a `/benchmark` precision pass.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Use the streaming helper as a context manager so the request is cancelled and the
connection released on exit.

Bad:
    stream = client.messages.stream(model="claude-sonnet-4-5", messages=msgs)
    for event in stream:
        ...

Good:
    with client.messages.stream(model="claude-sonnet-4-5", messages=msgs) as stream:
        for text in stream.text_stream:
            ...
"""

# Trailing attribute paths of the SDK streaming helpers (context managers).
_STREAM_TAILS: tuple[tuple[str, ...], ...] = (
    ("messages", "stream"),
    ("responses", "stream"),
    ("chat", "completions", "stream"),
)


def _attr_tail(func: ast.expr) -> list[str]:
    names: list[str] = []
    cur: ast.expr = func
    while isinstance(cur, ast.Attribute):
        names.append(cur.attr)
        cur = cur.value
    names.reverse()
    return names


def _is_stream_helper(node: ast.Call) -> bool:
    tail = _attr_tail(node.func)
    return any(len(tail) >= len(t) and tail[-len(t) :] == list(t) for t in _STREAM_TAILS)


def _is_context_managed(ctx: AnalysisContext, call: ast.Call) -> bool:
    """True if the call is (within) the context expression of a `with`/`async with`.

    Walks ancestors until a `withitem` (managed) or the enclosing statement (not).
    Reaching a `withitem` also covers `with closing(client.messages.stream(...)) as s`.
    """
    cur: ast.AST | None = ctx.tree.parent(call)
    while cur is not None:
        if isinstance(cur, ast.withitem):
            return True
        if isinstance(cur, ast.stmt):
            return False
        cur = ctx.tree.parent(cur)
    return False


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    tree = ctx.tree
    if not (tree.imported_roots & {"openai", "anthropic"}):
        return []  # `.stream()` is ambiguous; only tag when an SDK is imported (ADR-0016)
    findings: list[FindingDraft] = []
    for node in ast.walk(tree.tree):
        if not isinstance(node, ast.Call) or not _is_stream_helper(node):
            continue
        if _is_context_managed(ctx, node):
            continue
        findings.append(
            ctx.finding(
                node,
                "Streaming helper is not used as a context manager; the request is never "
                "guaranteed to be cancelled and the HTTP connection is leaked, exhausting "
                "the connection pool under load. Wrap it in `with ... as stream:`.",
            )
        )
    return findings


RULE = Rule(
    id="PLB-RES-010",
    title="Streamed response not used as a context manager",
    category="RES",
    pillar=Pillar.RELIABILITY,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "A leaked stream never releases its HTTP connection — under load the pool "
        "exhausts and workers hang."
    ),
    standards=("CWE-772", "CWE-400", "OWASP-LLM10"),
    remediation=REMEDIATION,
    detect=detect,
)
