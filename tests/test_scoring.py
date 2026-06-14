"""Scoring tests — ADR-0008. The D4 worked example is the normative vector."""

from __future__ import annotations

from plumbline.model import Confidence, Finding, Pillar, Severity
from plumbline.scoring import compute_scores
from plumbline.scoring.pillars import pillar_scores


def _f(pillar: Pillar, severity: Severity, confidence: Confidence) -> Finding:
    return Finding(
        rule_id="PLB-X-001",
        title="t",
        category="X",
        pillar=pillar,
        severity=severity,
        confidence=confidence,
        message="m",
        why_it_matters="w",
        file="a.py",
        line=1,
        column=0,
        end_line=None,
        snippet=None,
        standards=(),
        remediation="r",
        fingerprint="f",
    )


# The exact rows of ADR-0008 D4.
_D4_FINDINGS = [
    _f(Pillar.RELIABILITY, Severity.BLOCKER, Confidence.HIGH),  # 25
    _f(Pillar.RELIABILITY, Severity.CRITICAL, Confidence.HIGH),  # 10
    _f(Pillar.RELIABILITY, Severity.MAJOR, Confidence.MEDIUM),  # 1.2
    _f(Pillar.ARCHITECTURE, Severity.BLOCKER, Confidence.HIGH),  # 25
    _f(Pillar.ARCHITECTURE, Severity.MAJOR, Confidence.MEDIUM),  # 1.2
    _f(Pillar.HARNESS, Severity.MAJOR, Confidence.HIGH),  # 3
    _f(Pillar.ARCHITECTURE, Severity.MAJOR, Confidence.LOW),  # excluded
    _f(Pillar.SECURITY, Severity.BLOCKER, Confidence.HIGH),  # 25
]


def test_adr_0008_d4_worked_example_reproduced_exactly() -> None:
    scores = compute_scores(_D4_FINDINGS, semantic_node_count=8)
    assert scores.applicable
    assert scores.pillars[Pillar.RELIABILITY] == 64
    assert scores.pillars[Pillar.ARCHITECTURE] == 74
    assert scores.pillars[Pillar.HARNESS] == 97
    assert scores.pillars[Pillar.SECURITY] == 75
    assert scores.readiness == 75
    assert scores.model == "adr-0008"


def test_low_confidence_excluded_from_scoring() -> None:
    # The lone Architecture Low finding (#7) must not move the pillar.
    only_low = [_f(Pillar.ARCHITECTURE, Severity.BLOCKER, Confidence.LOW)]
    assert pillar_scores(only_low)[Pillar.ARCHITECTURE] == 100


def test_no_findings_is_all_100_when_applicable() -> None:
    scores = compute_scores([], semantic_node_count=5)
    assert scores.applicable
    assert all(v == 100 for v in scores.pillars.values())
    assert scores.readiness == 100


def test_zero_semantic_nodes_is_not_applicable() -> None:
    # ADR-0008 D3: no LLM/agent code -> N/A, never a misleading 100.
    scores = compute_scores(_D4_FINDINGS, semantic_node_count=0)
    assert not scores.applicable
    assert scores.readiness is None
    assert scores.pillars == {}


def test_pillar_floors_at_zero() -> None:
    # Four High Blockers in one pillar over-penalize; the score floors at 0.
    fs = [_f(Pillar.SECURITY, Severity.BLOCKER, Confidence.HIGH) for _ in range(4)]
    assert pillar_scores(fs)[Pillar.SECURITY] == 0
