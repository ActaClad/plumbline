"""Per-pillar scores — the capped linear penalty (ADR-0008 D1).

For each pillar, over its non-suppressed High/Medium-confidence findings:

    penalty(f)   = severity_weight × confidence_factor
    pillar_score = max(0, round(100 − Σ penalty))

Low-confidence findings are excluded from scoring (ADR-0001 D4). The score is a
dashboard, never the gate (CLAUDE.md §1.6). The formula is deliberately a linear
sum so a user can recompute any pillar by hand from the findings list.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ..model import Confidence, Finding, Pillar, Severity

SEVERITY_WEIGHT: Mapping[Severity, float] = {
    Severity.BLOCKER: 25.0,
    Severity.CRITICAL: 10.0,
    Severity.MAJOR: 3.0,
    Severity.MINOR: 1.0,
    Severity.INFO: 0.0,
}
# Low is absent on purpose: Low-confidence findings are excluded from scoring.
CONFIDENCE_FACTOR: Mapping[Confidence, float] = {
    Confidence.HIGH: 1.0,
    Confidence.MEDIUM: 0.4,
}


def penalty(finding: Finding) -> float:
    """The score penalty for one finding. 0 for Low confidence (excluded)."""
    factor = CONFIDENCE_FACTOR.get(finding.confidence)
    if factor is None:
        return 0.0
    return SEVERITY_WEIGHT[finding.severity] * factor


def pillar_scores(findings: Iterable[Finding]) -> dict[Pillar, int]:
    """0–100 per pillar (all four always present; a pillar with no findings = 100).
    `findings` must already be the active (non-suppressed) set (ADR-0006)."""
    totals: dict[Pillar, float] = dict.fromkeys(Pillar, 0.0)
    for f in findings:
        if f.confidence is Confidence.LOW:
            continue  # excluded from scoring (ADR-0001 D4)
        totals[f.pillar] += penalty(f)
    return {pillar: max(0, round(100 - total)) for pillar, total in totals.items()}
