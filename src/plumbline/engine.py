"""The analysis pipeline (architecture.md §3, detailed-design §3).

Orchestrates: discover files -> parse -> adapter-annotate -> (taint, M1) ->
file-scope rules -> project-scope rules -> finalize fingerprints -> dedupe ->
sort -> gate. Every per-file/per-rule failure is contained as an AnalyzerError
and never aborts the run (CLAUDE.md §4). The whole path is deterministic
(ADR-0002 D3): sorted file iteration, sorted findings, no clock/network/random.
"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import final

from .adapters import ADAPTERS
from .adapters.base import SemanticIndex, collect_semantics
from .baseline import load_baseline_fingerprints
from .config import Config, GateVerdict, evaluate_gate
from .core.ast_layer import ParseError, parse
from .core.derive import derive_semantics
from .core.evidence import collect_evidence
from .core.taint import TaintView, analyze_taint
from .model import AnalyzerError, Finding, FindingDraft, assign_fingerprints, finding_sort_key
from .rules.base import AnalysisContext, FileAnalysis, ProjectContext, Rule, RuleScope

# Directory names always pruned when default_excludes is on (ADR-0007 D2).
_DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "build",
        "dist",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".tox",
        ".eggs",
    }
)


@final
@dataclass(frozen=True, slots=True)
class SuppressedFinding:
    """A finding that fired but was suppressed (ADR-0006). Reported, but excluded
    from the gate and scoring. `kind` matches SARIF: external (baseline) | inSource."""

    finding: Finding
    kind: str  # "external" | "inSource"


@final
@dataclass(frozen=True, slots=True)
class ScanResult:
    findings: tuple[Finding, ...]  # active (non-suppressed) findings only
    suppressed: tuple[SuppressedFinding, ...]
    analyzer_errors: tuple[AnalyzerError, ...]
    gate: GateVerdict
    files_scanned: int
    rules_loaded: int
    semantic_node_count: int  # 0 => no LLM/agent code (N/A scoring, ADR-0008 D3)


def discover_files(root: Path, config: Config) -> list[str]:
    """Return POSIX-relative paths of `.py` files to scan, sorted (ADR-0002 D3).

    Honors config includes, `default_excludes`, and `[scan].exclude` globs.
    NOTE: full `.gitignore` semantics are deferred (see docs/backlog.md); the
    default-excludes set covers the common junk directories in the meantime.
    """
    scan = config.scan
    found: set[str] = set()
    for include in scan.include:
        base = (root / include).resolve()
        if base.is_file():
            if base.suffix == ".py":
                found.add(_rel(root, base))
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(
                d
                for d in dirnames
                if not (scan.default_excludes and (d in _DEFAULT_EXCLUDE_DIRS or d.startswith(".")))
            )
            for name in sorted(filenames):
                if name.endswith(".py"):
                    found.add(_rel(root, Path(dirpath) / name))
    return sorted(f for f in found if not _excluded(f, scan.exclude))


def _rel(root: Path, path: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        rel = path
    return str(PurePosixPath(rel))


def _excluded(rel: str, patterns: Sequence[str]) -> bool:
    return any(
        fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat.rstrip("/") + "/*")
        for pat in patterns
    )


def _analyze_file(root: Path, rel: str, errors: list[AnalyzerError]) -> FileAnalysis | None:
    try:
        source = (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(AnalyzerError(file=rel, stage="read", message=str(exc)))
        return None
    try:
        tree = parse(rel, source)
    except ParseError as exc:
        errors.append(AnalyzerError(file=rel, stage="parse", message=str(exc)))
        return None
    try:
        collected = collect_semantics(tree, ADAPTERS)
        collected.extend(derive_semantics(tree, collected))
        semantics = SemanticIndex(collected)
    except Exception as exc:  # noqa: BLE001 — adapter/derivation crash is contained
        errors.append(AnalyzerError(file=rel, stage="adapter", message=str(exc)))
        semantics = SemanticIndex([])
    try:
        taint = analyze_taint(tree, semantics)
    except Exception as exc:  # noqa: BLE001 — taint crash is contained
        errors.append(AnalyzerError(file=rel, stage="taint", message=str(exc)))
        taint = TaintView({}, {})
    return FileAnalysis(file=rel, tree=tree, semantics=semantics, taint=taint)


def scan(root: Path, config: Config, rules: Sequence[Rule]) -> ScanResult:
    errors: list[AnalyzerError] = []
    files = discover_files(root, config)

    analyses: list[FileAnalysis] = []
    for rel in files:
        analysis = _analyze_file(root, rel, errors)
        if analysis is not None:
            analyses.append(analysis)

    file_rules = [r for r in rules if r.scope is RuleScope.FILE]
    project_rules = [r for r in rules if r.scope is RuleScope.PROJECT]

    drafts: list[FindingDraft] = []
    for analysis in analyses:
        for rule in file_rules:
            ctx = AnalysisContext(analysis, rule, config)
            drafts.extend(_run(rule, ctx, analysis.file, errors))

    evidence = collect_evidence(root)
    for rule in project_rules:
        pctx = ProjectContext(analyses, rule, config, evidence)
        drafts.extend(_run(rule, pctx, "<project>", errors))

    findings = _dedupe(assign_fingerprints(drafts))
    findings.sort(key=finding_sort_key)

    active, suppressed = _apply_suppressions(root, config, analyses, findings, errors)

    gate = evaluate_gate(active, config.gate)  # suppressed excluded (ADR-0006)
    semantic_nodes = sum(len(a.semantics) for a in analyses)
    return ScanResult(
        findings=tuple(active),
        suppressed=tuple(suppressed),
        analyzer_errors=tuple(errors),
        gate=gate,
        files_scanned=len(analyses),
        rules_loaded=len(rules),
        semantic_node_count=semantic_nodes,
    )


def _apply_suppressions(
    root: Path,
    config: Config,
    analyses: list[FileAnalysis],
    findings: list[Finding],
    errors: list[AnalyzerError],
) -> tuple[list[Finding], list[SuppressedFinding]]:
    """Partition findings into active and suppressed (baseline + inline, ADR-0006).

    Baseline beats inline when both match. Bare `# plumb: ignore` directives are
    reported as analyzer errors — blanket suppression must not be silent (D6).
    """
    baseline_fps = load_baseline_fingerprints(root / config.baseline.file)
    inline: dict[tuple[str, int], frozenset[str]] = {}
    for a in analyses:
        for lineno, ids in a.tree.suppressions.by_line.items():
            inline[(a.file, lineno)] = ids
        for lineno in a.tree.suppressions.invalid_lines:
            errors.append(
                AnalyzerError(
                    file=a.file,
                    stage="suppression",
                    message=f"bare '# plumb: ignore' on line {lineno} has no rule id; ignored",
                )
            )

    active: list[Finding] = []
    suppressed: list[SuppressedFinding] = []
    for f in findings:
        if f.fingerprint in baseline_fps:
            suppressed.append(SuppressedFinding(f, "external"))
        elif f.rule_id in inline.get((f.file, f.line), frozenset()):
            suppressed.append(SuppressedFinding(f, "inSource"))
        else:
            active.append(f)
    return active, suppressed


def _run(
    rule: Rule, ctx: AnalysisContext | ProjectContext, file: str, errors: list[AnalyzerError]
) -> list[FindingDraft]:
    try:
        return list(rule.detect(ctx))
    except Exception as exc:  # noqa: BLE001 — a crashing detector is contained
        errors.append(AnalyzerError(file=file, stage=f"rule:{rule.id}", message=str(exc)))
        return []


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen: set[str] = set()
    out: list[Finding] = []
    for f in findings:
        if f.fingerprint not in seen:
            seen.add(f.fingerprint)
            out.append(f)
    return out
