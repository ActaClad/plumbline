"""Dogfood: Plumbline must run cleanly on its own source (H1 hardening).

Scanning a real, non-trivial Python codebase — its own `src/` — is the cheapest
proof the analyzer doesn't crash, doesn't false-positive on ordinary code, and
produces a deterministic result. It found two real issues when first run: a
suppression-parser false positive on a doc comment, and EVAL-001 on the (now
suppressed, documented) enrichment layer.
"""

from __future__ import annotations

from pathlib import Path

from plumbline.config import Config
from plumbline.engine import scan
from plumbline.reporters.json import render_json
from plumbline.rules.base import discover_rules

SRC = Path(__file__).resolve().parents[1] / "src"
RULES = discover_rules()


def test_self_scan_has_no_analyzer_errors() -> None:
    result = scan(SRC, Config(), RULES)
    assert result.analyzer_errors == (), [
        (e.file, e.stage, e.message) for e in result.analyzer_errors
    ]


def test_self_scan_is_clean_and_gate_passes() -> None:
    result = scan(SRC, Config(), RULES)
    # The only finding (EVAL-001 on the AI layer) is suppressed with a reason.
    assert result.findings == ()
    assert result.gate.passed


def test_self_scan_is_deterministic() -> None:
    a = scan(SRC, Config(), RULES)
    b = scan(SRC, Config(), RULES)
    assert render_json(a) == render_json(b)
