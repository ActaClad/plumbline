"""PLB-RES-001 — LLM/tool call without timeout.

An LLM call whose timeout is *explicitly disabled* (`timeout=None`) can hang
indefinitely and exhaust the worker pool, taking the service down. This is the
genuinely unbounded case: a bare call relies on the SDK's finite default timeout
(reported by the adapter with `timeout_source="sdk_default"`) and is NOT flagged
— flagging idiomatic, default-bounded code is exactly the noise that gets an
analyzer uninstalled (CLAUDE.md §1.4, detailed-design §9.4).

Ships at Medium confidence until a precision number lands in /benchmark
(CLAUDE.md §1.3); the signal itself is deterministic (an explicit `timeout=None`),
so promotion to High is expected in M3.
"""

from __future__ import annotations

from ...model import Confidence, FindingDraft, Known, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Set an explicit, finite timeout on the call or the client — never disable it.

Bad:
    client.chat.completions.create(model="gpt-4o", messages=msgs, timeout=None)

Good:
    client.chat.completions.create(model="gpt-4o", messages=msgs, timeout=30)
    # or once, on the client:
    client = OpenAI(timeout=30)
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        timeout = sn.attrs.get("timeout")
        if isinstance(timeout, Known) and timeout.value is None:
            findings.append(
                ctx.finding(
                    sn.node,
                    "LLM call has its timeout explicitly disabled (timeout=None); it can hang "
                    "indefinitely and exhaust the worker pool.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-RES-001",
    title="LLM/tool call without timeout",
    category="RES",
    pillar=Pillar.RELIABILITY,
    severity=Severity.BLOCKER,
    confidence=Confidence.MEDIUM,  # -> High in M3 once /benchmark measures precision
    why_it_matters=(
        "A model/tool call with no timeout can hang indefinitely and exhaust the "
        "worker pool, taking the service down."
    ),
    remediation=REMEDIATION,
    detect=detect,
)
