"""PLB-AGT-001 — Agent loop without a max-iteration limit.

An agent that can iterate without a hard cap runs away: it burns unbounded cost
and may never terminate when the model keeps "deciding" to take another step.
This is the canonical "one rule, three frameworks" detector — it consumes two
normalized tags and fires identically across LangChain, CrewAI, and hand-rolled
loops (ADR-0012):

- `AGENT_CREATE` with `max_iterations = Known(None)` — the cap was *explicitly*
  removed (`AgentExecutor(..., max_iterations=None)`, `Agent(..., max_iter=None)`).
  A bare constructor is bounded by the framework default and is NOT flagged
  (ADR-0012 D4), exactly as RES-001 ignores the SDK's default timeout.
- `AGENT_LOOP` with `has_iteration_cap = Known(False)` — a hand-rolled
  `while True:` driving a model with no counter/range bound.
"""

from __future__ import annotations

from ...model import Confidence, FindingDraft, Known, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Put a hard upper bound on agent iterations, independent of the model's own
stop decision.

LangChain:
    AgentExecutor(agent=a, tools=t, max_iterations=10)   # not None

CrewAI:
    Agent(role=..., goal=..., max_iter=10)               # not None

Hand-rolled loop:
    for _ in range(MAX_STEPS):
        step = llm.invoke(...)
        if done(step):
            break
    else:
        raise RuntimeError("agent did not converge in MAX_STEPS")
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.AGENT_CREATE):
        mi = sn.attrs.get("max_iterations")
        if isinstance(mi, Known) and mi.value is None:
            findings.append(
                ctx.finding(
                    sn.node,
                    "Agent constructed with its iteration cap removed "
                    "(max_iterations=None); it can iterate without bound.",
                )
            )
    for sn in ctx.semantics.by_tag(SemanticTag.AGENT_LOOP):
        cap = sn.attrs.get("has_iteration_cap")
        if isinstance(cap, Known) and cap.value is False:
            findings.append(
                ctx.finding(
                    sn.node,
                    "Hand-rolled agent loop drives a model with no max-iteration "
                    "cap; add a hard step bound as a backstop.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-AGT-001",
    title="Agent loop without max-iteration limit",
    category="AGT",
    pillar=Pillar.ARCHITECTURE,
    severity=Severity.BLOCKER,
    confidence=Confidence.MEDIUM,  # promoted to High via the /benchmark commit (ADR-0012)
    why_it_matters=(
        "An agent loop with no hard iteration cap runs away — unbounded cost, may never terminate."
    ),
    standards=("OWASP-AGENTIC",),
    remediation=REMEDIATION,
    detect=detect,
)
