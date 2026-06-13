"""Precision/recall benchmark harness (CLAUDE.md §1.3, §4).

A rule may not ship at High confidence without a measured precision number here.
The corpus is labeled with inline expectation markers:

    client.chat.completions.create(model="m", timeout=None)  # plumb-expect: PLB-RES-001

A produced finding whose (file, line, rule) matches a marker is a true positive;
a produced finding with no matching marker is a false positive; a marker with no
matching finding is a false negative (a miss). Per rule:

    precision = TP / (TP + FP)      recall = TP / (TP + FN)

Precision gates High confidence (>= 0.90). Recall is informational — the v1
taint boundary (ADR-0003 D6) deliberately trades recall for precision.

This harness is deterministic and does no network I/O; it simply runs the engine
over the corpus and compares against the markers.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import final

from .config import Config
from .engine import scan
from .rules.base import Rule, discover_rules

HIGH_CONFIDENCE_PRECISION = 0.90

_MARKER_RE = re.compile(r"#\s*plumb-expect:\s*(?P<ids>[A-Z0-9,\s\-]+)")


@final
@dataclass(frozen=True, slots=True)
class RuleMetrics:
    rule_id: str
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float | None:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else None

    @property
    def recall(self) -> float | None:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else None

    @property
    def meets_high(self) -> bool:
        p = self.precision
        return p is not None and p >= HIGH_CONFIDENCE_PRECISION


@final
@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    metrics: tuple[RuleMetrics, ...]
    cases: int  # number of corpus files
    markers: int  # number of expectation markers

    def for_rule(self, rule_id: str) -> RuleMetrics | None:
        return next((m for m in self.metrics if m.rule_id == rule_id), None)


def _read_markers(corpus_root: Path) -> tuple[dict[tuple[str, int, str], None], int]:
    """Map (posix-relpath, line, rule_id) -> expected, plus the marker count."""
    expected: dict[tuple[str, int, str], None] = {}
    count = 0
    for path in sorted(corpus_root.rglob("*.py")):
        rel = path.relative_to(corpus_root).as_posix()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = _MARKER_RE.search(line)
            if match is None:
                continue
            for rid in (part.strip() for part in match.group("ids").split(",")):
                if rid:
                    expected[(rel, lineno, rid)] = None
                    count += 1
    return expected, count


def run_benchmark(corpus_root: Path, rules: Sequence[Rule] | None = None) -> BenchmarkReport:
    """Scan the corpus and compute per-rule metrics against the markers."""
    rules = list(rules) if rules is not None else discover_rules()
    expected, marker_count = _read_markers(corpus_root)

    result = scan(corpus_root, Config(), rules)
    produced = {(f.file, f.line, f.rule_id) for f in result.findings}
    expected_keys = set(expected)

    rule_ids = sorted({r.id for r in rules} | {k[2] for k in expected_keys})
    metrics: list[RuleMetrics] = []
    for rid in rule_ids:
        prod = {k for k in produced if k[2] == rid}
        exp = {k for k in expected_keys if k[2] == rid}
        tp = len(prod & exp)
        metrics.append(
            RuleMetrics(
                rule_id=rid,
                true_positives=tp,
                false_positives=len(prod - exp),
                false_negatives=len(exp - prod),
            )
        )

    cases = sum(1 for _ in corpus_root.rglob("*.py"))
    return BenchmarkReport(metrics=tuple(metrics), cases=cases, markers=marker_count)


def render_report(report: BenchmarkReport) -> str:
    """A stable markdown table of the metrics."""
    lines = [
        f"# Benchmark precision report ({report.cases} files, {report.markers} markers)",
        "",
        "| Rule | TP | FP | FN | Precision | Recall | High-eligible |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in report.metrics:
        lines.append(
            f"| {m.rule_id} | {m.true_positives} | {m.false_positives} | {m.false_negatives} "
            f"| {_pct(m.precision)} | {_pct(m.recall)} | {'yes' if m.meets_high else 'no'} |"
        )
    return "\n".join(lines) + "\n"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"
