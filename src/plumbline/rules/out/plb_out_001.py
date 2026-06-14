"""PLB-OUT-001 — LLM output parsed as JSON without error handling.

`json.loads(model_output)` with no guard crashes on the first malformed
generation — and models produce malformed JSON regularly (markdown fences,
truncation, prose preambles). This is a taint rule: it fires only when the
argument to `json.loads`/`json.load` actually carries LLM output (via the taint
engine) and the call is not inside a `try` that catches a relevant exception.
"""

from __future__ import annotations

import ast

from ...core.taint import TaintLabel
from ...model import Confidence, FindingDraft, Pillar, Severity
from .._ast_helpers import enclosing_try_body, try_catches
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Validate model output against a schema and handle parse failure (retry or fallback).

Bad:
    data = json.loads(resp.choices[0].message.content)

Good:
    try:
        data = json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        data = repair_or_retry(...)
    # better: use the provider's structured-output / response_format and validate
"""

# Exceptions whose presence on an enclosing try means the parse is guarded.
_HANDLED = frozenset({"JSONDecodeError", "ValueError", "Exception", "BaseException"})


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for node in ast.walk(ctx.tree.tree):
        if not isinstance(node, ast.Call) or not _is_json_parse(node.func) or not node.args:
            continue
        arg = node.args[0]
        if not ctx.taint.is_tainted(arg, TaintLabel.LLM_OUTPUT):
            continue
        try_node = enclosing_try_body(ctx.tree, node)
        if try_node is not None and try_catches(try_node, _HANDLED):
            continue
        findings.append(
            ctx.finding(
                node,
                "LLM output is parsed with json.loads and no error handling; a malformed "
                "generation will raise and crash the request.",
            )
        )
    return findings


def _is_json_parse(func: ast.expr) -> bool:
    # json.loads / json.load (attribute form only — the common, unambiguous case)
    return (
        isinstance(func, ast.Attribute)
        and func.attr in {"loads", "load"}
        and isinstance(func.value, ast.Name)
        and func.value.id == "json"
    )


RULE = Rule(
    id="PLB-OUT-001",
    title="LLM output parsed as JSON without error handling",
    category="OUT",
    pillar=Pillar.RELIABILITY,
    severity=Severity.CRITICAL,
    confidence=Confidence.HIGH,
    why_it_matters=(
        "`json.loads` on raw LLM output with no guard crashes on the first malformed generation."
    ),
    remediation=REMEDIATION,
    detect=detect,
)
