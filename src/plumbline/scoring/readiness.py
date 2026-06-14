"""The composite Readiness Score (ADR-0008 D2/D3).

    Readiness = round(0.35·Reliability + 0.25·Architecture
                    + 0.20·Harness     + 0.20·Security)

Weights are hard-coded (a configurable composite is incomparable across repos).
If a scan finds zero semantic nodes — no LLM/agent code — every score is **N/A**,
not 100 (D3): a non-AI repo is not "100/100 production-ready agentic code".

NOTE the naming invariant (CLAUDE.md §1.10): this is the **Readiness Score**; the
"Trust" family of metrics belongs exclusively to AgentGuard, never reproduced
here. (Worded to avoid the forbidden two-word phrase the CI guardrail greps for.)
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import final

from ..model import Finding, Pillar
from .pillars import pillar_scores

PILLAR_WEIGHTS: Mapping[Pillar, float] = {
    Pillar.RELIABILITY: 0.35,
    Pillar.ARCHITECTURE: 0.25,
    Pillar.HARNESS: 0.20,
    Pillar.SECURITY: 0.20,
}
SCORING_MODEL = "adr-0008"


@final
@dataclass(frozen=True, slots=True)
class Scores:
    """The scoring result. When `applicable` is False (no agentic code, D3),
    `pillars` is empty and `readiness` is None — reporters render that as N/A."""

    applicable: bool
    pillars: Mapping[Pillar, int]
    readiness: int | None
    model: str = field(default=SCORING_MODEL)


def compute_scores(findings: Iterable[Finding], semantic_node_count: int) -> Scores:
    """Pillar + Readiness scores from the active findings. N/A when there is no
    LLM/agent code at all (ADR-0008 D3)."""
    if semantic_node_count == 0:
        return Scores(applicable=False, pillars={}, readiness=None)
    pillars = pillar_scores(findings)
    readiness = round(sum(PILLAR_WEIGHTS[p] * pillars[p] for p in Pillar))
    return Scores(applicable=True, pillars=pillars, readiness=readiness)
