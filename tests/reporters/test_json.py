"""JSON reporter tests — shape + determinism (architecture.md §6)."""

from __future__ import annotations

import json
from pathlib import Path

from plumbline.config import Config
from plumbline.engine import scan
from plumbline.reporters.json import render_json, to_json_obj
from plumbline.rules.base import discover_rules

RULES = discover_rules()


def _scan_finding(tmp_path: Path) -> object:
    (tmp_path / "agent.py").write_text(
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "c.chat.completions.create(model='m', timeout=None)\n"
    )
    return scan(tmp_path, Config(), RULES)


def test_json_shape(tmp_path: Path) -> None:
    obj = to_json_obj(_scan_finding(tmp_path))  # type: ignore[arg-type]
    assert obj["version"] == 1
    assert obj["summary"]["finding_count"] == 1
    f = obj["findings"][0]
    assert f["rule_id"] == "PLB-RES-001"
    assert f["pillar"] == "RELIABILITY"
    assert f["severity"] == "Blocker"
    assert f["fingerprint"]
    assert obj["gate"]["passed"] is False


def test_json_is_valid_and_deterministic(tmp_path: Path) -> None:
    result = _scan_finding(tmp_path)
    a = render_json(result)  # type: ignore[arg-type]
    b = render_json(result)  # type: ignore[arg-type]
    assert a == b
    json.loads(a)  # parses


def test_json_includes_suppressed(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "c.chat.completions.create(model='m', timeout=None)  # plumb: ignore[PLB-RES-001]\n"
    )
    obj = to_json_obj(scan(tmp_path, Config(), RULES))
    assert obj["findings"] == []
    assert len(obj["suppressed"]) == 1
    assert obj["suppressed"][0]["suppression"] == "inSource"
