"""PLB-SEC-005 — Untrusted content in a raw SQL query string.

A query built from model output or untrusted input via f-string/concat and passed
to `cursor.execute(...)` is SQL injection. The precision crux (see `_sinks`): only
the *query-string* arg is taint-checked, so a parameterized query —
`execute("… WHERE id = ?", (user_id,))` — has a constant (untainted) query and
stays silent; the tainted bind params are safe.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, Severity
from .._sinks import sql_query_sink
from .._taint_flow import UNTRUSTED, first_label, witness_flow
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Use parameterized queries — never build SQL by string interpolation.

Bad:
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")

Good:
    cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for node in ast.walk(ctx.tree.tree):
        if not isinstance(node, ast.Call):
            continue
        query = sql_query_sink(node)
        if query is None:
            continue
        label = first_label(ctx.taint, query, UNTRUSTED)
        if label is None:
            continue
        findings.append(
            ctx.finding(
                node,
                f"Untrusted {label.value} is interpolated into a raw SQL query — SQL injection.",
                code_flow=witness_flow(ctx.taint, ctx.file, query, label, node, "executed as SQL"),
            )
        )
    return findings


RULE = Rule(
    id="PLB-SEC-005",
    title="LLM-controlled SQL / query injection",
    category="SEC",
    pillar=Pillar.SECURITY,
    severity=Severity.BLOCKER,
    confidence=Confidence.HIGH,  # measured 100% precision in /benchmark
    why_it_matters=(
        "A SQL query built from untrusted content by string interpolation is SQL injection."
    ),
    standards=("CWE-89",),
    remediation=REMEDIATION,
    detect=detect,
)
