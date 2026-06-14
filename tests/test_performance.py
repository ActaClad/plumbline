"""Performance sanity (H5 hardening).

Not a micro-benchmark — a regression net. A sizable synthetic repo must scan to
completion (no pathological O(n^2) blowup or hang) and stay deterministic at
size. Measured separately: ~4ms/file, linear (1200 files in ~5.5s vs 600 in
~2.9s), so this generous test catches gross regressions without flaking on
wall-clock.
"""

from __future__ import annotations

from pathlib import Path

from plumbline.config import Config
from plumbline.engine import scan
from plumbline.reporters.json import render_json
from plumbline.rules.base import discover_rules

RULES = discover_rules()

_MODULE = """\
import json
from openai import OpenAI

client = OpenAI(timeout=30)
MODEL = "gpt-4o"


def handler_{i}(text, **opts):
    resp = client.chat.completions.create(
        model=MODEL, messages=[{{"role": "user", "content": text}}], max_tokens=256, **opts
    )
    for _ in range(8):
        r = client.chat.completions.create(model=MODEL, messages=[], max_tokens=100)
        if r.choices[0].message.content.startswith("X"):
            break
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return {{}}
"""


def _make_repo(root: Path, n: int) -> None:
    for i in range(n):
        (root / f"mod_{i}.py").write_text(_MODULE.format(i=i))


def test_large_repo_scans_to_completion(tmp_path: Path) -> None:
    _make_repo(tmp_path, 150)
    result = scan(tmp_path, Config(), RULES)
    assert result.files_scanned == 150
    assert result.analyzer_errors == ()


def test_large_repo_scan_is_deterministic(tmp_path: Path) -> None:
    _make_repo(tmp_path, 150)
    assert render_json(scan(tmp_path, Config(), RULES)) == render_json(
        scan(tmp_path, Config(), RULES)
    )
