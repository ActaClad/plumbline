"""`plumb` CLI entrypoint (ADR-0007 D5).

Exit codes: 0 gate passed · 1 gate failed · 2 usage/config error ·
3 internal/rule-load error.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import click
from rich.console import Console

from .config import Config, ConfigError, load_config
from .engine import ScanResult, scan
from .reporters import cli as cli_reporter
from .reporters.sarif import write_sarif
from .rules.base import Rule, RuleLoadError, discover_rules

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
def scan_command(
    paths: tuple[Path, ...], config_path: Path | None, sarif_path: Path | None
) -> None:
    """Scan PATHS (default: current directory) for reliability/architecture defects."""
    root = _scan_root(paths)
    try:
        loaded = load_config(root, explicit_path=config_path)
        rules = discover_rules()
        loaded.config.validate_against_rules(frozenset(r.id for r in rules))
    except ConfigError as exc:
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

    result = scan(root, config, rules)
    cli_reporter.render(_out, _err, result)

    _maybe_write_sarif(result, rules, config, sarif_path)
    raise SystemExit(0 if result.gate.passed else 1)


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


def _scan_root(paths: tuple[Path, ...]) -> Path:
    if not paths:
        return Path.cwd()
    first = paths[0]
    return (first if first.is_dir() else first.parent).resolve()


def _maybe_write_sarif(
    result: ScanResult, rules: list[Rule], config: Config, sarif_path: Path | None
) -> None:
    path = sarif_path
    if path is None and "sarif" in config.output.formats:
        path = Path(config.output.sarif_path)
    if path is not None:
        write_sarif(result, rules, str(path))
        _err.print(f"[dim]wrote SARIF to {path}[/dim]")


if __name__ == "__main__":  # pragma: no cover
    main()
