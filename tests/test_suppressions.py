"""Suppression handling: inline + baseline (ADR-0006 D5/D6)."""

from __future__ import annotations

from pathlib import Path

from plumbline.baseline import render_baseline, write_baseline
from plumbline.config import Config
from plumbline.engine import scan
from plumbline.rules.base import discover_rules

RULES = discover_rules()

_DISABLED = (
    "from openai import OpenAI\n"
    "c = OpenAI()\n"
    "r = c.chat.completions.create(model='m', timeout=None){suffix}\n"
)


def _write(root: Path, suffix: str = "") -> None:
    (root / "agent.py").write_text(_DISABLED.format(suffix=suffix))


def test_finding_active_without_suppression(tmp_path: Path) -> None:
    _write(tmp_path)
    result = scan(tmp_path, Config(), RULES)
    assert len(result.findings) == 1
    assert result.suppressed == ()
    assert not result.gate.passed


def test_inline_suppression_moves_finding_to_suppressed(tmp_path: Path) -> None:
    _write(tmp_path, suffix="  # plumb: ignore[PLB-RES-001]")
    result = scan(tmp_path, Config(), RULES)
    assert result.findings == ()
    assert len(result.suppressed) == 1
    assert result.suppressed[0].kind == "inSource"
    assert result.gate.passed  # suppressed -> excluded from gate


def test_inline_suppression_wrong_rule_id_does_not_suppress(tmp_path: Path) -> None:
    _write(tmp_path, suffix="  # plumb: ignore[PLB-SEC-002]")
    result = scan(tmp_path, Config(), RULES)
    assert len(result.findings) == 1
    assert result.suppressed == ()


def test_bare_ignore_reported_as_analyzer_error(tmp_path: Path) -> None:
    _write(tmp_path, suffix="  # plumb: ignore")
    result = scan(tmp_path, Config(), RULES)
    assert len(result.findings) == 1  # NOT suppressed (bare ignore is invalid)
    assert any(e.stage == "suppression" for e in result.analyzer_errors)


def test_baseline_suppresses_known_fingerprint(tmp_path: Path) -> None:
    _write(tmp_path)
    first = scan(tmp_path, Config(), RULES)
    write_baseline(tmp_path / ".plumbline-baseline.json", list(first.findings))

    second = scan(tmp_path, Config(), RULES)
    assert second.findings == ()
    assert len(second.suppressed) == 1
    assert second.suppressed[0].kind == "external"
    assert second.gate.passed


def test_baseline_does_not_suppress_new_finding(tmp_path: Path) -> None:
    _write(tmp_path)
    # Baseline a different fingerprint -> the real finding stays active.
    (tmp_path / ".plumbline-baseline.json").write_text(
        render_baseline([])  # empty baseline
    )
    result = scan(tmp_path, Config(), RULES)
    assert len(result.findings) == 1


def test_baseline_round_trips_fingerprint(tmp_path: Path) -> None:
    _write(tmp_path)
    result = scan(tmp_path, Config(), RULES)
    fp = result.findings[0].fingerprint
    write_baseline(tmp_path / "bl.json", list(result.findings))
    from plumbline.baseline import load_baseline_fingerprints

    assert fp in load_baseline_fingerprints(tmp_path / "bl.json")
