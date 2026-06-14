"""PLB-RES-002 — Retries explicitly disabled on an LLM/tool call.

Transient provider errors (429, 5xx) are normal at scale. The OpenAI/Anthropic
SDKs retry automatically (default max_retries=2). Setting `max_retries=0` turns
those transient blips into avoidable user-facing failures. As with RES-001, a
bare call relies on the SDK default and is NOT flagged; only an explicit disable
(`max_retries=0`) fires — a deterministic, no-false-positive signal.
"""

from __future__ import annotations

from ...model import Confidence, FindingDraft, Known, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Keep the SDK's automatic retries, or add your own backoff — don't set retries to 0.

Bad:
    client = OpenAI(max_retries=0)
    client.chat.completions.create(model="gpt-4o", messages=msgs)

Good:
    client = OpenAI(max_retries=3)          # or leave the SDK default (2)
    client.chat.completions.create(model="gpt-4o", messages=msgs)
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        retries = sn.attrs.get("max_retries")
        if isinstance(retries, Known) and retries.value == 0:
            findings.append(
                ctx.finding(
                    sn.node,
                    "LLM call has retries disabled (max_retries=0); transient provider "
                    "errors (429, 5xx) become user-facing failures.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-RES-002",
    title="No retry on LLM/tool call",
    category="RES",
    pillar=Pillar.RELIABILITY,
    severity=Severity.CRITICAL,
    confidence=Confidence.HIGH,
    why_it_matters=(
        "Transient provider errors (429, 5xx) with no retry become avoidable user-facing failures."
    ),
    remediation=REMEDIATION,
    detect=detect,
)
