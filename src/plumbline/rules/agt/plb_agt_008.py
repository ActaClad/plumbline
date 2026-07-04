"""PLB-AGT-008 — AutoGen team with no turn cap and no termination condition.

Unlike CrewAI/LangChain (which ship a finite default iteration cap), AutoGen's
AgentChat teams — `RoundRobinGroupChat`, `SelectorGroupChat`, `Swarm`,
`MagenticOneGroupChat` — have **no default turn limit**. A team constructed with
neither `max_turns` nor a `termination_condition` runs until the model happens to
stop — i.e. potentially forever, burning unbounded tokens and hanging the worker.

Detection is a self-contained AST rule (there is no AutoGen adapter): when the
SDK is imported, a team constructor with **neither** bound keyword fires. It does
not guess about `**kwargs` — an explicit `max_turns=` or `termination_condition=`
suppresses it. Ships **Medium/advisory** until a `/benchmark` precision pass.

Standards: OWASP LLM10 (unbounded consumption); CWE-835 (loop with unreachable
exit).
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Give an AutoGen team a hard stop — a turn cap, a termination condition, or both.
AutoGen has no default turn limit, so without one the conversation can loop forever.

Bad:
    team = RoundRobinGroupChat([writer, critic])

Good:
    from autogen_agentchat.conditions import MaxMessageTermination
    team = RoundRobinGroupChat(
        [writer, critic],
        termination_condition=MaxMessageTermination(20),   # or max_turns=20
    )
"""

_TEAM_CTORS = frozenset(
    {"RoundRobinGroupChat", "SelectorGroupChat", "Swarm", "MagenticOneGroupChat"}
)
_BOUND_KWARGS = frozenset({"max_turns", "termination_condition"})


def _ctor_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else None


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    tree = ctx.tree
    if not (tree.imported_roots & {"autogen_agentchat", "autogen"}):
        return []
    findings: list[FindingDraft] = []
    for node in ast.walk(tree.tree):
        if not isinstance(node, ast.Call) or _ctor_name(node) not in _TEAM_CTORS:
            continue
        if any(kw.arg in _BOUND_KWARGS for kw in node.keywords):
            continue  # an explicit bound is present
        findings.append(
            ctx.finding(
                node,
                f"AutoGen team {_ctor_name(node)!r} has neither max_turns nor a "
                "termination_condition; AutoGen has no default turn cap, so the "
                "conversation can loop without bound.",
            )
        )
    return findings


RULE = Rule(
    id="PLB-AGT-008",
    title="AutoGen team with no turn cap or termination condition",
    category="AGT",
    pillar=Pillar.ARCHITECTURE,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "An AutoGen team with no turn cap and no termination condition can loop "
        "forever — there is no default limit to fall back on."
    ),
    standards=("CWE-835", "OWASP-LLM10"),
    remediation=REMEDIATION,
    detect=detect,
)
