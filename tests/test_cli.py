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


def test_scan_prints_readiness_score(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "agent.py",
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "c.chat.completions.create(model='m', timeout=None, max_tokens=10)\n",
    )
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert "Readiness Score:" in result.output
    assert "Reliability" in result.output


def test_scan_writes_html_report(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "x = 1\n")
    out = tmp_path / "report.html"
    result = CliRunner().invoke(main, ["scan", str(tmp_path), "--html", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    text = out.read_text()
    assert "<html" in text and "Plumbline" in text
    assert "http://" not in text and "https://" not in text  # offline


def test_score_does_not_drive_the_gate(tmp_path: Path) -> None:
    # CLAUDE.md §1.6: the gate is the CI mechanism, the score is a dashboard.
    # An SSRF (Critical/Medium) + project-scope advisories are all non-gating, so
    # the gate PASSES (exit 0) even though the Readiness Score is well under 100.
    _write(
        tmp_path,
        "agent.py",
        "import requests\n"
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "def f(q):\n"
        "    r = c.chat.completions.create(model='m', timeout=5, max_tokens=10)\n"
        "    return requests.get(r.choices[0].message.content, timeout=5)\n",
    )
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0  # gate passed
    assert "gate passed" in result.output
    assert "PLB-SEC-007" in result.output  # the Medium finding fired
    assert "Readiness Score: 100" not in result.output  # but the score reflects it


def test_ai_enrichment_does_not_change_exit_code(tmp_path: Path, monkeypatch) -> None:
    # §1.1 firewall at the CLI: AI rewrites remediation but the gate/exit are
    # decided on the deterministic result. RES-001 (Blocker) still fails the gate.
    from plumbline import cli

    class _Fake:
        def enrich(self, finding):  # noqa: ANN001, ANN201
            return "AI-TAILORED fix"

    monkeypatch.setattr(cli, "build_enricher", lambda config: (_Fake(), None))
    _write(
        tmp_path,
        "agent.py",
        "from openai import OpenAI\nc = OpenAI()\n"
        "c.chat.completions.create(model='m', timeout=None, max_tokens=10)\n",
    )
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 1  # gate still fails — enrichment cannot change it
    assert "(AI-assisted)" in result.output


def test_ai_enabled_without_key_emits_notice(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, ".plumbline.toml", "[ai]\nenrich_remediation = true\n")
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0  # detection/exit unchanged
    assert "static remediation" in result.output  # but the user is told


def test_export_skills_writes_a_pack(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    result = CliRunner().invoke(main, ["export-skills", "--out", str(out)])
    assert result.exit_code == 0
    assert (out / "SKILL.md").exists()
    assert (out / "manifest.json").exists()
    assert any((out / "rules").glob("PLB-*.md"))
    assert "prevention" in result.output.lower()  # positioning surfaced


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


_DISABLED = (
    "from openai import OpenAI\nc = OpenAI()\n"
    "c.chat.completions.create(model='m', timeout=None){suffix}\n"
)


def test_strict_analyzer_errors_fails_gate(tmp_path: Path) -> None:
    _write(tmp_path, "bad.py", "def f(:\n")
    ok = CliRunner().invoke(main, ["scan", str(tmp_path)])
    strict = CliRunner().invoke(main, ["scan", str(tmp_path), "--strict-analyzer-errors"])
    assert ok.exit_code == 0
    assert strict.exit_code == 1


def test_scan_writes_json_and_sarif(tmp_path: Path) -> None:
    _write(tmp_path, "agent.py", _DISABLED.format(suffix=""))
    sarif, js = tmp_path / "o.sarif", tmp_path / "o.json"
    result = CliRunner().invoke(
        main, ["scan", str(tmp_path / "agent.py"), "--sarif", str(sarif), "--json", str(js)]
    )
    assert result.exit_code == 1
    assert sarif.is_file() and js.is_file()


def test_baseline_then_scan_passes(tmp_path: Path) -> None:
    _write(tmp_path, "agent.py", _DISABLED.format(suffix=""))
    bl = tmp_path / ".plumbline-baseline.json"
    made = CliRunner().invoke(main, ["baseline", str(tmp_path), "--output", str(bl)])
    assert made.exit_code == 0 and bl.is_file()
    # With the finding baselined, a scan using that baseline passes the gate.
    cfg = tmp_path / ".plumbline.toml"
    cfg.write_text(f'[baseline]\nfile = "{bl.name}"\n')
    rescan = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert rescan.exit_code == 0
    assert "suppressed" in rescan.output


def test_inline_suppression_passes_gate(tmp_path: Path) -> None:
    _write(tmp_path, "agent.py", _DISABLED.format(suffix="  # plumb: ignore[PLB-RES-001]"))
    result = CliRunner().invoke(main, ["scan", str(tmp_path / "agent.py")])
    assert result.exit_code == 0
    assert "suppressed" in result.output


def test_bad_baseline_exits_two(tmp_path: Path) -> None:
    _write(tmp_path, "agent.py", "x = 1\n")
    (tmp_path / ".plumbline.toml").write_text('[baseline]\nfile = "bl.json"\n')
    (tmp_path / "bl.json").write_text('{"version":1,"algorithm":"v2","findings":[]}')
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 2
    assert "config error" in result.output
