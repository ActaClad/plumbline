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

# Weights are 0.35 / 0.25 / 0.20 / 0.20 (ADR-0008 D2), expressed here in integer
# hundredths — the Readiness sum is computed in integer
# hundredths and rounded half-up `(sum + 50)//100`, NOT via float `round()`.
# Two reasons: float `round` is banker's (half-to-even), so a Readiness landing on
# an exact .5 (e.g. Reliability 90 / others 100 -> 96.5) would round to 96 while a
# human hand-recomputing gets 97 — breaking ADR-0008's "hand-auditable" promise;
# and float noise (0.35 is inexact) would otherwise decide near-.5 cases by
# representation error. This reproduces the D4 vector exactly (7530 -> 75).
_WEIGHT_HUNDREDTHS: Mapping[Pillar, int] = {
    Pillar.RELIABILITY: 35,
    Pillar.ARCHITECTURE: 25,
    Pillar.HARNESS: 20,
    Pillar.SECURITY: 20,
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
    hundredths = sum(_WEIGHT_HUNDREDTHS[p] * pillars[p] for p in Pillar)
    readiness = (hundredths + 50) // 100  # integer half-up (see _WEIGHT_HUNDREDTHS)
    return Scores(applicable=True, pillars=pillars, readiness=readiness)
