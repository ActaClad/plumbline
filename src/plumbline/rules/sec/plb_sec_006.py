"""PLB-SEC-006 — LLM output rendered as HTML without escaping (XSS).

Model output reaching an *unescaped* HTML sink — `render_template_string`,
`Markup(...)`/`markupsafe.Markup` — is stored/reflected XSS. Jinja2's
`render_template` autoescapes by default and is NOT flagged (see `_sinks`); only
the explicitly-unsafe paths are, which is what keeps this rule quiet on the
overwhelming majority of (autoescaped) rendering.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, Severity
from .._sinks import html_sink
from .._taint_flow import UNTRUSTED, first_label, witness_flow
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Treat model output as untrusted text; let the templating layer escape it.

Bad:
    return render_template_string(llm_html)      # unescaped -> XSS
    return Markup(llm_output)

Good:
    return render_template("page.html", body=llm_output)   # Jinja2 autoescapes
    # or escape explicitly: markupsafe.escape(llm_output)
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for node in ast.walk(ctx.tree.tree):
        if not isinstance(node, ast.Call):
            continue
        content = html_sink(node)
        if content is None:
            continue
        label = first_label(ctx.taint, content, UNTRUSTED)
        if label is None:
            continue
        findings.append(
            ctx.finding(
                node,
                f"Untrusted {label.value} is rendered as HTML without escaping — cross-site "
                "scripting (XSS).",
                code_flow=witness_flow(
                    ctx.taint, ctx.file, content, label, node, "rendered as unescaped HTML"
                ),
            )
        )
    return findings


RULE = Rule(
    id="PLB-SEC-006",
    title="LLM output rendered as HTML without sanitization",
    category="SEC",
    pillar=Pillar.SECURITY,
    severity=Severity.CRITICAL,
    confidence=Confidence.HIGH,  # measured 100% precision in /benchmark
    why_it_matters=(
        "Model output rendered through an unescaped HTML sink is reflected/stored XSS."
    ),
    standards=("CWE-79", "OWASP-LLM02"),
    remediation=REMEDIATION,
    detect=detect,
)
