"""End-to-end engine tests + the determinism harness (ADR-0002 D3)."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from plumbline.config import Config
from plumbline.engine import discover_files, scan


def _write(root: Path, rel: str, src: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(src))


# --- file discovery -----------------------------------------------------------


def test_discovers_py_files_sorted(tmp_path: Path) -> None:
    _write(tmp_path, "b.py", "x = 1\n")
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, "pkg/c.py", "x = 1\n")
    assert discover_files(tmp_path, Config()) == ["a.py", "b.py", "pkg/c.py"]


def test_default_excludes_prune_junk_dirs(tmp_path: Path) -> None:
    _write(tmp_path, "app.py", "x = 1\n")
    _write(tmp_path, ".venv/lib.py", "x = 1\n")
    _write(tmp_path, "node_modules/m.py", "x = 1\n")
    assert discover_files(tmp_path, Config()) == ["app.py"]


def test_exclude_glob_applied(tmp_path: Path) -> None:
    from plumbline.config import ScanConfig

    _write(tmp_path, "app.py", "x = 1\n")
    _write(tmp_path, "tests/test_x.py", "x = 1\n")
    cfg = Config(scan=ScanConfig(exclude=("tests/",)))
    assert discover_files(tmp_path, cfg) == ["app.py"]


def test_non_python_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, "readme.md", "hi\n")
    assert discover_files(tmp_path, Config()) == ["a.py"]


# --- scanning -----------------------------------------------------------------


def test_scan_empty_repo_passes_gate(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "x = 1\n")
    result = scan(tmp_path, Config(), rules=[])
    assert result.findings == ()
    assert result.files_scanned == 1
    assert result.rules_loaded == 0
    assert result.gate.passed
    assert result.semantic_node_count == 0


def test_scan_counts_semantic_nodes(tmp_path: Path) -> None:
    _write(tmp_path, "agent.py", "from openai import OpenAI\nc = OpenAI()\n")
    result = scan(tmp_path, Config(), rules=[])
    assert result.semantic_node_count >= 1  # LLM_CLIENT_CREATE detected


def test_parse_error_becomes_analyzer_error_not_abort(tmp_path: Path) -> None:
    _write(tmp_path, "good.py", "x = 1\n")
    _write(tmp_path, "bad.py", "def f(:\n")
    result = scan(tmp_path, Config(), rules=[])
    assert result.files_scanned == 1  # good.py analyzed
    assert any(e.stage == "parse" and e.file == "bad.py" for e in result.analyzer_errors)
    assert result.gate.passed  # analyzer errors don't fail the gate by default


# --- determinism (ADR-0002 D3) ------------------------------------------------


def test_double_run_in_process_is_equal(tmp_path: Path) -> None:
    _write(tmp_path, "agent.py", "from openai import OpenAI\nc = OpenAI(timeout=5)\n")
    _write(tmp_path, "other.py", "y = 2\n")
    assert scan(tmp_path, Config(), rules=[]) == scan(tmp_path, Config(), rules=[])


_DIGEST_SCRIPT = """
import json, sys
from pathlib import Path
from plumbline.config import Config
from plumbline.engine import scan
r = scan(Path(sys.argv[1]), Config(), rules=[])
print(json.dumps({
    "findings": [f.fingerprint for f in r.findings],
    "files": r.files_scanned,
    "semantic_nodes": r.semantic_node_count,
    "gate": r.gate.passed,
}, sort_keys=True))
"""


def test_cross_process_determinism_across_hashseeds(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "agent.py",
        "from openai import OpenAI\nc = OpenAI()\nc.chat.completions.create(model='m')\n",
    )
    script = tmp_path / "_digest.py"
    script.write_text(_DIGEST_SCRIPT)

    def run(seed: str) -> str:
        env = {"PYTHONHASHSEED": seed, "PATH": __import__("os").environ.get("PATH", "")}
        out = subprocess.run(
            [sys.executable, str(script), str(tmp_path)],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        return out.stdout

    assert run("0") == run("1")  # output identical regardless of hash seed
