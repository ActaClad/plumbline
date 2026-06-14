"""Benchmark harness tests (CLAUDE.md §1.3)."""

from __future__ import annotations

from pathlib import Path

from plumbline.benchmark import render_report, run_benchmark
from plumbline.rules.base import discover_rules

REPO_ROOT = Path(__file__).resolve().parents[1]
RULES = discover_rules()

_DISABLED = (
    "from openai import OpenAI\n"
    "c = OpenAI()\n"
    "c.chat.completions.create(model='m', timeout=None){marker}\n"
)
_GOOD = "from openai import OpenAI\nc = OpenAI()\nc.chat.completions.create(model='m', timeout=5)\n"


def _corpus(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    for name, src in files.items():
        (root / name).write_text(src)
    return root


def test_true_positive_matches_marker(tmp_path: Path) -> None:
    root = _corpus(tmp_path, {"a.py": _DISABLED.format(marker="  # plumb-expect: PLB-RES-001")})
    m = run_benchmark(root, RULES).for_rule("PLB-RES-001")
    assert m is not None
    assert (m.true_positives, m.false_positives, m.false_negatives) == (1, 0, 0)
    assert m.precision == 1.0


def test_unmarked_finding_is_false_positive(tmp_path: Path) -> None:
    # timeout=None but no marker -> the scanner fires, so it's a false positive.
    root = _corpus(tmp_path, {"a.py": _DISABLED.format(marker="")})
    m = run_benchmark(root, RULES).for_rule("PLB-RES-001")
    assert m is not None
    assert (m.true_positives, m.false_positives) == (0, 1)
    assert m.precision == 0.0


def test_marker_without_finding_is_false_negative(tmp_path: Path) -> None:
    # marker says RES-001 expected, but a safe call never fires -> a miss.
    src = _GOOD.replace("timeout=5)", "timeout=5)  # plumb-expect: PLB-RES-001")
    m = run_benchmark(_corpus(tmp_path, {"a.py": src}), RULES).for_rule("PLB-RES-001")
    assert m is not None
    assert (m.true_positives, m.false_negatives) == (0, 1)
    assert m.recall == 0.0


def test_idiomatic_code_yields_no_false_positives(tmp_path: Path) -> None:
    m = run_benchmark(_corpus(tmp_path, {"a.py": _GOOD}), RULES).for_rule("PLB-RES-001")
    assert m is not None
    assert m.false_positives == 0


def test_precision_none_when_no_positives(tmp_path: Path) -> None:
    root = _corpus(tmp_path, {"a.py": "x = 1\n"})
    m = run_benchmark(root, RULES).for_rule("PLB-RES-001")
    assert m is not None and m.precision is None and not m.meets_high


def test_report_is_deterministic(tmp_path: Path) -> None:
    root = _corpus(tmp_path, {"a.py": _DISABLED.format(marker="  # plumb-expect: PLB-RES-001")})
    assert render_report(run_benchmark(root, RULES)) == render_report(run_benchmark(root, RULES))


def test_every_high_confidence_rule_meets_precision_on_corpus() -> None:
    # The committed corpus is the gate: any rule shipping at High must hold
    # >= 90% precision (and in practice 0 FP) here (CLAUDE.md §1.3).
    report = run_benchmark(REPO_ROOT / "benchmark" / "corpus", RULES)
    high_rules = [r.id for r in RULES if r.confidence.label == "High"]
    assert high_rules, "expected at least one High-confidence rule"
    for rid in high_rules:
        m = report.for_rule(rid)
        assert m is not None and m.true_positives >= 1, f"{rid}: no TP in corpus"
        assert m.false_positives == 0, f"{rid}: false positives in corpus"
        assert m.meets_high, f"{rid}: below the High precision threshold"
