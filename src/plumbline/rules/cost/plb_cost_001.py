"""PLB-COST-001 — No max_tokens / output cap on generation.

A generation with no output bound can run to the model's full context length —
a cost spike and a latency/reliability risk (a slow, huge response ties up the
request). Fires when **every** output-cap parameter is provably absent at the
call; a value set explicitly (including the reasoning-model caps
`max_completion_tokens` / `max_output_tokens`), or passed unresolvably via
`**kwargs` (UNKNOWN), stays silent. Major severity: advisory in the default gate,
not a build-breaker.
"""

from __future__ import annotations

from ...model import ABSENT, Confidence, FindingDraft, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

# Any one of these bounds the output; reasoning models use `max_completion_tokens`
# (Chat Completions) or `max_output_tokens` (Responses API) instead of `max_tokens`.
_CAP_PARAMS = ("max_tokens", "max_completion_tokens", "max_output_tokens")

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
        if all(sn.attrs.get(cap) is ABSENT for cap in _CAP_PARAMS):
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
