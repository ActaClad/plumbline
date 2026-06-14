"""PLB-COST-001 — No max_tokens / output cap on generation.

A generation with no output bound can run to the model's full context length —
a cost spike and a latency/reliability risk (a slow, huge response ties up the
request). Fires when `max_tokens` is provably absent at the call; a value set
explicitly, or passed unresolvably via `**kwargs` (UNKNOWN), stays silent.
Major severity: advisory in the default gate, not a build-breaker.
"""

from __future__ import annotations

from ...model import ABSENT, Confidence, FindingDraft, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Set an explicit output cap so a generation can't run to the full context window.

Bad:
    client.chat.completions.create(model="gpt-4o", messages=msgs)

Good:
    client.chat.completions.create(model="gpt-4o", messages=msgs, max_tokens=512)
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        if sn.attrs.get("max_tokens") is ABSENT:
            findings.append(
                ctx.finding(
                    sn.node,
                    "LLM generation has no max_tokens cap; output can run to the full "
                    "context window, spiking cost and latency.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-COST-001",
    title="No max_tokens / output cap on generation",
    category="COST",
    pillar=Pillar.RELIABILITY,
    severity=Severity.MAJOR,
    confidence=Confidence.HIGH,
    why_it_matters="No output bound is both a cost risk and a latency/reliability risk.",
    remediation=REMEDIATION,
    detect=detect,
)
