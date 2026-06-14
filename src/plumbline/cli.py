"""`plumb` CLI entrypoint (ADR-0007 D5).

Exit codes: 0 gate passed · 1 gate failed · 2 usage/config error ·
3 internal/rule-load error.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .baseline import BaselineError, write_baseline
from .benchmark import render_report, run_benchmark
from .config import Config, ConfigError, load_config
from .engine import ScanResult, scan
from .enrichment import build_enricher, enrich_result
from .reporters import cli as cli_reporter
from .reporters.html import write_html
from .reporters.json import write_json
from .reporters.sarif import write_sarif
from .rules.base import Rule, RuleLoadError, discover_rules
from .skills.export import PACK_FORMAT, write_skill_pack

_err = Console(stderr=True)
_out = Console()


@click.group()
@click.version_option(package_name="actaclad-plumbline", prog_name="plumb")
def main() -> None:
    """Plumbline — the reliability and architecture analyzer for agentic systems."""


@main.command("scan")
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--config", "config_path", type=click.Path(path_type=Path), help="Config file path.")
@click.option("--sarif", "sarif_path", type=click.Path(path_type=Path), help="Write SARIF here.")
@click.option("--json", "json_path", type=click.Path(path_type=Path), help="Write JSON here.")
@click.option(
    "--html", "html_path", type=click.Path(path_type=Path), help="Write an HTML report here."
)
@click.option(
    "--strict-analyzer-errors",
    is_flag=True,
    help="Fail the gate (exit 1) if any file/rule raised an analyzer error.",
)
def scan_command(
    paths: tuple[Path, ...],
    config_path: Path | None,
    sarif_path: Path | None,
    json_path: Path | None,
    html_path: Path | None,
    strict_analyzer_errors: bool,
) -> None:
    """Scan PATHS (default: current directory) for reliability/architecture defects."""
    root = _scan_root(paths)
    config, rules = _load(root, config_path, paths)

    result = _run_scan(root, config, rules)
    # The gate/exit code below are decided on the DETERMINISTIC result, before
    # any AI runs. Enrichment only rewrites remediation text (ADR-0015 D1).
    failed = not result.gate.passed or (strict_analyzer_errors and result.analyzer_errors)
    result = _maybe_enrich(result, config)

    cli_reporter.render(_out, _err, result)
    _write_outputs(result, rules, config, sarif_path, json_path, html_path)
    raise SystemExit(1 if failed else 0)


def _maybe_enrich(result: ScanResult, config: Config) -> ScanResult:
    """Optional AI remediation enrichment (ADR-0015). Off by default; never
    touches detection/gate. Enabled-but-unavailable emits a notice, not silence."""
    enricher, notice = build_enricher(config)
    if notice is not None:
        _err.print(f"[yellow]notice:[/yellow] {notice}")
    return enrich_result(result, enricher) if enricher is not None else result


@main.command("baseline")
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--config", "config_path", type=click.Path(path_type=Path), help="Config file path.")
@click.option("--output", "out_path", type=click.Path(path_type=Path), help="Baseline file path.")
def baseline_command(
    paths: tuple[Path, ...], config_path: Path | None, out_path: Path | None
) -> None:
    """Scan and write a baseline of current findings (accept them; gate on new ones)."""
    root = _scan_root(paths)
    config, rules = _load(root, config_path, paths)
    result = _run_scan(root, config, rules)
    # Baseline the union of active + already-suppressed findings (the full set).
    findings = [*result.findings, *(sf.finding for sf in result.suppressed)]
    target = out_path or (root / config.baseline.file)
    write_baseline(target, findings)
    _out.print(f"Wrote {len(findings)} finding(s) to baseline [bold]{target}[/bold].")


@main.command("benchmark")
@click.argument(
    "corpus",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="benchmark/corpus",
)
@click.option("--md", "md_path", type=click.Path(path_type=Path), help="Write the report here.")
def benchmark_command(corpus: Path, md_path: Path | None) -> None:
    """Measure per-rule precision/recall against the labeled corpus."""
    try:
        rules = discover_rules()
    except RuleLoadError as exc:
        _err.print(f"[red]rule load error:[/red] {exc}")
        raise SystemExit(3) from exc
    report = run_benchmark(corpus, rules)
    text = render_report(report)
    _out.print(text)
    if md_path is not None:
        md_path.write_text(text, encoding="utf-8")
        _err.print(f"[dim]wrote report to {md_path}[/dim]")


@main.command("export-skills")
@click.option(
    "--out",
    "out_dir",
    type=click.Path(path_type=Path),
    default="skill-pack",
    show_default=True,
    help="Directory to write the skill pack into.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice([PACK_FORMAT]),
    default=PACK_FORMAT,
    show_default=True,
    help="Render target.",
)
@click.option(
    "--fixtures",
    "fixtures_dir",
    type=click.Path(path_type=Path),
    default="fixtures",
    help="Fixtures root used for the bad/good examples.",
)
def export_skills_command(out_dir: Path, fmt: str, fixtures_dir: Path) -> None:
    """Export the rules as a generation-time skill pack (prevention, NOT the gate)."""
    try:
        rules = discover_rules()
    except RuleLoadError as exc:
        _err.print(f"[red]rule load error:[/red] {exc}")
        raise SystemExit(3) from exc
    written = write_skill_pack(out_dir, rules, fixtures_dir, __version__)
    _out.print(
        f"Wrote a {fmt} pack of {len(rules)} rule(s) to [bold]{out_dir}[/bold] "
        f"({len(written)} files)."
    )
    _err.print("[dim]This pack is prevention, not a gate — run 'plumb scan' to verify.[/dim]")


@main.command("rules")
def rules_command() -> None:
    """List the rules Plumbline has loaded."""
    try:
        rules = discover_rules()
    except RuleLoadError as exc:
        _err.print(f"[red]rule load error:[/red] {exc}")
        raise SystemExit(3) from exc
    if not rules:
        _out.print("No rules loaded.")
        return
    for rule in rules:
        _out.print(
            f"[bold]{rule.id}[/bold]  {rule.title}  "
            f"[dim]({rule.severity.label}/{rule.confidence.label}, {rule.pillar.display})[/dim]"
        )
    _out.print(f"\n{len(rules)} rule(s) loaded.")


def _load(
    root: Path, config_path: Path | None, paths: tuple[Path, ...]
) -> tuple[Config, list[Rule]]:
    try:
        loaded = load_config(root, explicit_path=config_path)
        rules = discover_rules()
        loaded.config.validate_against_rules(frozenset(r.id for r in rules))
    except (ConfigError, BaselineError) as exc:
        _err.print(f"[red]config error:[/red] {exc}")
        raise SystemExit(2) from exc
    except RuleLoadError as exc:
        _err.print(f"[red]rule load error:[/red] {exc}")
        raise SystemExit(3) from exc

    for notice in loaded.notices:
        _err.print(f"[yellow]notice:[/yellow] {notice}")

    config = loaded.config
    if paths:
        # Absolute includes so the engine's root/include join is path-correct
        # whether a file or a directory was given.
        includes = tuple(str(p.resolve()) for p in paths)
        config = replace(config, scan=replace(config.scan, include=includes))
    return config, rules


def _run_scan(root: Path, config: Config, rules: list[Rule]) -> ScanResult:
    try:
        return scan(root, config, rules)
    except BaselineError as exc:
        _err.print(f"[red]config error:[/red] {exc}")
        raise SystemExit(2) from exc


def _scan_root(paths: tuple[Path, ...]) -> Path:
    if not paths:
        return Path.cwd()
    first = paths[0]
    return (first if first.is_dir() else first.parent).resolve()


def _write_outputs(
    result: ScanResult,
    rules: list[Rule],
    config: Config,
    sarif_path: Path | None,
    json_path: Path | None,
    html_path: Path | None = None,
) -> None:
    sarif = sarif_path or (
        Path(config.output.sarif_path) if "sarif" in config.output.formats else None
    )
    if sarif is not None:
        write_sarif(result, rules, str(sarif))
        _err.print(f"[dim]wrote SARIF to {sarif}[/dim]")
    js = json_path or (Path(config.output.json_path) if "json" in config.output.formats else None)
    if js is not None:
        write_json(result, str(js))
        _err.print(f"[dim]wrote JSON to {js}[/dim]")
    if html_path is not None:
        write_html(result, str(html_path))
        _err.print(f"[dim]wrote HTML report to {html_path}[/dim]")


if __name__ == "__main__":  # pragma: no cover
    main()
