"""PLB-GOV-001 — PII flows into a prompt without redaction.

Sending personal data (email, phone, SSN, …) to a third-party model provider with
no redaction is a data-governance failure. Taint rule on the `PII` label (seeded
from PII-named parameters/fields): fires when PII reaches the message/prompt
argument of an LLM call. Medium — the PII source is a name heuristic.
"""

from __future__ import annotations

import ast

from ...core.taint import TaintLabel
from ...model import Confidence, FindingDraft, Pillar, SemanticTag, Severity
from .._taint_flow import witness_flow
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Redact or tokenize PII before sending it to a model provider.

Bad:
    client.chat.completions.create(messages=[{"role": "user", "content": email}])

Good:
    client.chat.completions.create(
        messages=[{"role": "user", "content": redact_pii(email)}]
    )
"""

_PROMPT_ARGS: frozenset[str] = frozenset({"messages", "prompt", "input"})


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        call = sn.node
        if not isinstance(call, ast.Call):
            continue
        for kw in call.keywords:
            if kw.arg in _PROMPT_ARGS and ctx.taint.is_tainted(kw.value, TaintLabel.PII):
                findings.append(
                    ctx.finding(
                        call,
                        "PII flows into the model prompt with no redaction; personal data is "
                        "sent to a third-party provider.",
                        code_flow=witness_flow(
                            ctx.taint,
                            ctx.file,
                            kw.value,
                            TaintLabel.PII,
                            call,
                            "sent in the prompt",
                        ),
                    )
                )
                break
    return findings


RULE = Rule(
    id="PLB-GOV-001",
    title="PII flows into a prompt without redaction",
    category="GOV",
    pillar=Pillar.SECURITY,
    severity=Severity.CRITICAL,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "Sending unredacted PII to a third-party model provider is a data-governance violation."
    ),
    standards=("NIST-AI-RMF:MAP",),
    remediation=REMEDIATION,
    detect=detect,
)
