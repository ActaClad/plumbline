"""PLB-MDL-003 — High temperature on a tool-calling / agentic path.

When a model call has `tools=` configured, the model is *selecting an action*.
A high sampling temperature on that call makes the action selection
nondeterministic — the same input can pick different tools or arguments across
runs — which is untestable and a reliability hazard on an agentic path. Higher
temperatures belong on creative free-text generation, not on action selection.

Precision discipline (CLAUDE.md §1.3/§1.4, tri-state ADR-0004 D2):
- Fires only on an *explicit* `Known` temperature above the threshold. An ABSENT
  temperature is NOT flagged even though the provider default is high (~1.0):
  doing so would flag essentially every tool call that omits the argument —
  unacceptable noise. We require the developer to have set a high value.
- `tools` must be present (not ABSENT). A bare completion with no tools is
  creative generation and never fires, regardless of temperature.
- Advisory (Medium): the 0.3 threshold is a heuristic, not a law.

Naturally a raw OpenAI/Anthropic-SDK rule — that is where `tools=` and
`temperature=` sit on the same `create()` call. LangChain binds tools separately
(`.bind_tools()`), so its temperature-on-tool-path case is a backlog recall item.
"""

from __future__ import annotations

from ...model import (
    ABSENT,
    Confidence,
    FindingDraft,
    Known,
    Pillar,
    Resolved,
    SemanticTag,
    Severity,
)
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Lower the temperature for action-selection calls (those with `tools=`); reserve
higher temperatures for creative free-text generation.

Bad:
    client.chat.completions.create(
        model="gpt-4o", temperature=0.9, tools=TOOLS, messages=msgs,
    )

Good:
    client.chat.completions.create(
        model="gpt-4o", temperature=0, tools=TOOLS, messages=msgs,
    )
"""

# Above this, sampling meaningfully perturbs action selection. Heuristic — the
# rule ships advisory (Medium), so the exact line is not load-bearing.
_TEMP_THRESHOLD = 0.3


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        temp = sn.attrs.get("temperature", ABSENT)
        tools = sn.attrs.get("tools", ABSENT)
        if isinstance(temp, Known) and _is_high(temp.value) and _tools_present(tools):
            findings.append(
                ctx.finding(
                    sn.node,
                    f"Tool-calling completion runs at temperature {temp.value} (> "
                    f"{_TEMP_THRESHOLD}); high temperature makes action selection "
                    "nondeterministic and untestable. Lower it for tool/action calls.",
                )
            )
    return findings


def _is_high(value: object) -> bool:
    # bool is a subclass of int — `temperature=True` is not a real temperature.
    return (
        isinstance(value, int | float) and not isinstance(value, bool) and value > _TEMP_THRESHOLD
    )


def _tools_present(tools: Resolved) -> bool:
    """True if `tools=` is configured. A Known value must be truthy (an explicit
    `tools=None`/`[]` is not a tool path); an UNKNOWN (e.g. `tools=a_variable`)
    still means the call passes tools, so it counts as present."""
    if isinstance(tools, Known):
        return bool(tools.value)
    return tools is not ABSENT


RULE = Rule(
    id="PLB-MDL-003",
    title="High temperature on a tool-calling / agentic path",
    category="MDL",
    pillar=Pillar.RELIABILITY,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "High sampling temperature on a call that selects tools makes action selection "
        "nondeterministic and untestable."
    ),
    remediation=REMEDIATION,
    detect=detect,
)
