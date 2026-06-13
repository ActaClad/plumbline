"""CLI end-to-end tests (ADR-0007 D5 exit codes)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from plumbline.cli import main


def _write(root: Path, rel: str, src: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(src)


def test_scan_clean_repo_exits_zero(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "x = 1\n")
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 findings" in result.output
    assert "gate passed" in result.output


def test_rules_command_lists_discovered_rules(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["rules"])
    assert result.exit_code == 0
    assert "PLB-RES-001" in result.output
    assert "rule(s) loaded." in result.output


def test_invalid_config_exits_two(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, ".plumbline.toml", "[gate]\nfail_on_severity = ['Nope']\n")
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 2
    assert "config error" in result.output


def test_missing_path_exits_two(tmp_path: Path) -> None:
    # click validates path existence -> usage error, exit 2.
    result = CliRunner().invoke(main, ["scan", str(tmp_path / "nope")])
    assert result.exit_code == 2


def test_scan_single_file_path_is_analyzed(tmp_path: Path) -> None:
    # Regression: a file path (not a dir) must actually be scanned.
    f = tmp_path / "agent.py"
    f.write_text(
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "c.chat.completions.create(model='m', timeout=None)\n"
    )
    result = CliRunner().invoke(main, ["scan", str(f)])
    assert result.exit_code == 1  # PLB-RES-001 fires -> gate fails
    assert "PLB-RES-001" in result.output
    assert "1 file(s)" in result.output


def test_scan_reports_analyzer_error(tmp_path: Path) -> None:
    _write(tmp_path, "bad.py", "def f(:\n")
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "analyzer error" in result.output
