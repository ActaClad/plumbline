"""PLB-AGT-002 — No termination/exit condition in a custom agent loop.

A `while True:` driving a model with no reachable `break`/`return` cannot stop:
the only way out is an exception or the process being killed. Distinct from
AGT-001 (which is about a hard *cap*): a loop can have a goal-based exit yet no
cap (AGT-001 fires, AGT-002 does not), or a cap yet — for a `while True` — no
goal exit. This rule consumes the `has_goal_exit` property of `AGENT_LOOP`
(ADR-0012 D3), firing only on `Known(False)`.
"""

from __future__ import annotations

from ...model import Confidence, FindingDraft, Known, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Give the loop a reachable exit tied to a goal or stop signal.

Bad:
    while True:
        step = llm.invoke(state)
        state = apply(step)        # no break/return — never stops

Good:
    while True:
        step = llm.invoke(state)
        if step.is_final:
            return step.answer     # reachable goal exit
        state = apply(step)
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.AGENT_LOOP):
        goal = sn.attrs.get("has_goal_exit")
        if isinstance(goal, Known) and goal.value is False:
            findings.append(
                ctx.finding(
                    sn.node,
                    "Agent loop has no reachable termination condition "
                    "(while True with no break/return); it can only exit by crashing.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-AGT-002",
    title="No termination/exit condition in custom agent loop",
    category="AGT",
    pillar=Pillar.ARCHITECTURE,
    severity=Severity.CRITICAL,
    confidence=Confidence.MEDIUM,  # promoted to High via the /benchmark commit (ADR-0012)
    why_it_matters=(
        "A model-driven `while True` with no reachable break/return can only exit by crashing."
    ),
    remediation=REMEDIATION,
    detect=detect,
)
