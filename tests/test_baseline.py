"""Baseline file format + load (ADR-0006 D5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plumbline.baseline import (
    BaselineError,
    load_baseline_fingerprints,
    render_baseline,
)
from plumbline.model import Confidence, Finding, Pillar, Severity


def _finding(fp: str) -> Finding:
    return Finding(
        rule_id="PLB-RES-001",
        title="t",
        category="RES",
        pillar=Pillar.RELIABILITY,
        severity=Severity.BLOCKER,
        confidence=Confidence.MEDIUM,
        message="m",
        why_it_matters="w",
        file="app/agent.py",
        line=1,
        column=0,
        end_line=None,
        snippet=None,
        standards=(),
        remediation="r",
        fingerprint=fp,
    )


def test_render_has_version_and_algorithm() -> None:
    doc = json.loads(render_baseline([_finding("abc123")]))
    assert doc["version"] == 1
    assert doc["algorithm"] == "v1"
    assert doc["findings"][0]["fingerprint"] == "abc123"


def test_render_is_deterministic_and_sorted() -> None:
    a = render_baseline([_finding("zzz"), _finding("aaa")])
    b = render_baseline([_finding("aaa"), _finding("zzz")])
    assert a == b  # input order does not matter


def test_missing_file_is_empty_set(tmp_path: Path) -> None:
    assert load_baseline_fingerprints(tmp_path / "nope.json") == frozenset()


def test_algorithm_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "bl.json"
    p.write_text(json.dumps({"version": 1, "algorithm": "v2", "findings": []}))
    with pytest.raises(BaselineError, match="algorithm"):
        load_baseline_fingerprints(p)


def test_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "bl.json"
    p.write_text("{not json")
    with pytest.raises(BaselineError, match="invalid baseline"):
        load_baseline_fingerprints(p)
