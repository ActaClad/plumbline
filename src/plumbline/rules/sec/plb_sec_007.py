"""PLB-SEC-007 — SSRF via a tool/LLM-controlled URL.

Model output or a tool argument used as the URL of an outbound HTTP call lets the
model reach internal services and cloud metadata endpoints (SSRF). Ships
**Medium**, not High: static analysis cannot see a host allow-list or validation
applied upstream, so this fires even when the URL is in fact constrained — a real
residual false-positive that makes it advisory rather than build-gating.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, Severity
from .._sinks import http_url_sink
from .._taint_flow import UNTRUSTED, first_label, witness_flow
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Constrain outbound URLs derived from model/tool output.

- Allow-list destination hosts; reject anything else.
- Block private/loopback/link-local ranges and cloud metadata IPs (169.254.169.254).
- Resolve and re-check the host after redirects.

Plumbline can't see an allow-list applied elsewhere — if the URL is already
constrained, suppress this finding.
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for node in ast.walk(ctx.tree.tree):
        if not isinstance(node, ast.Call):
            continue
        url = http_url_sink(node)
        if url is None:
            continue
        label = first_label(ctx.taint, url, UNTRUSTED)
        if label is None:
            continue
        findings.append(
            ctx.finding(
                node,
                f"{label.value} is used as an outbound request URL — server-side request "
                "forgery (SSRF) if the host is not constrained.",
                code_flow=witness_flow(ctx.taint, ctx.file, url, label, node, "fetched as a URL"),
            )
        )
    return findings


RULE = Rule(
    id="PLB-SEC-007",
    title="SSRF via tool/LLM-controlled URL",
    category="SEC",
    pillar=Pillar.SECURITY,
    severity=Severity.CRITICAL,
    confidence=Confidence.MEDIUM,  # stays Medium: allow-lists are invisible to static analysis
    why_it_matters=(
        "A model/tool-controlled URL on an outbound call enables SSRF to internal/metadata hosts."
    ),
    standards=("CWE-918",),
    remediation=REMEDIATION,
    detect=detect,
)
