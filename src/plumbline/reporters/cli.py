"""Human-readable terminal reporter (architecture.md §6).

Groups findings by file, shows what/where/why/how for each, and ends with the
gate verdict. Severity-colored via rich. M1 scope; HTML/score summary land in M7.
"""

from __future__ import annotations

from rich.console import Console

from ..engine import ScanResult
from ..model import Finding, Severity

_COLOR: dict[Severity, str] = {
    Severity.BLOCKER: "bold red",
    Severity.CRITICAL: "red",
    Severity.MAJOR: "yellow",
    Severity.MINOR: "cyan",
    Severity.INFO: "dim",
}


def render(out: Console, err: Console, result: ScanResult) -> None:
    by_file: dict[str, list[Finding]] = {}
    for f in result.findings:
        by_file.setdefault(f.file, []).append(f)

    for file in sorted(by_file):
        out.print(f"\n[bold underline]{file}[/bold underline]")
        for f in by_file[file]:
            _render_finding(out, f)

    for e in result.analyzer_errors:
        err.print(f"[yellow]analyzer error[/yellow] ({e.stage}) {e.file}: {e.message}")

    _render_summary(out, result)


def _suppressed_note(result: ScanResult) -> str:
    n = len(result.suppressed)
    return f" [dim]({n} suppressed)[/dim]" if n else ""


def _render_finding(out: Console, f: Finding) -> None:
    color = _COLOR.get(f.severity, "white")
    loc = f"{f.file}:{f.line}" + (f":{f.column + 1}" if f.column is not None else "")
    std = f"  [dim]{', '.join(f.standards)}[/dim]" if f.standards else ""
    out.print(
        f"  [{color}]{f.severity.label}[/{color}]"
        f"[dim]/{f.confidence.label}[/dim] [bold]{f.rule_id}[/bold] {loc}{std}"
    )
    out.print(f"    {f.message}")
    out.print(f"    [dim]why:[/dim] {f.why_it_matters}")
    fix = f.remediation.strip().splitlines()
    if fix:
        out.print(f"    [dim]fix:[/dim] {fix[0]}")


def _render_summary(out: Console, result: ScanResult) -> None:
    n = len(result.findings)
    verb = "finding" if n == 1 else "findings"
    gate = (
        "[green]gate passed[/green]" if result.gate.passed else "[bold red]gate failed[/bold red]"
    )
    out.print(
        f"\n{n} {verb} across {result.files_scanned} file(s); "
        f"{result.rules_loaded} rule(s) loaded.{_suppressed_note(result)} {gate}"
    )
    if not result.gate.passed:
        for reason in result.gate.reasons:
            out.print(f"  [red]✗[/red] {reason}")
