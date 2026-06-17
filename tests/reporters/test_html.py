"""HTML reporter tests — offline, deterministic, escaped, scored (M7)."""

from __future__ import annotations

from pathlib import Path

from plumbline.config import GateVerdict
from plumbline.engine import ScanResult
from plumbline.model import Confidence, Finding, Pillar, Severity
from plumbline.reporters.html import render_html

_EXAMPLE_REPORT = (
    Path(__file__).resolve().parents[2] / "docs" / "examples" / "llm-sample-report.html"
)


def _finding(message: str = "m", why: str = "w") -> Finding:
    return Finding(
        rule_id="PLB-SEC-002",
        title="t",
        category="SEC",
        pillar=Pillar.SECURITY,
        severity=Severity.BLOCKER,
        confidence=Confidence.HIGH,
        message=message,
        why_it_matters=why,
        file="app.py",
        line=10,
        column=4,
        end_line=None,
        snippet=None,
        standards=("CWE-95",),
        remediation="r",
        fingerprint="abc123",
    )


def _result(findings: list[Finding], semantic_nodes: int = 5, passed: bool = False) -> ScanResult:
    return ScanResult(
        findings=tuple(findings),
        suppressed=(),
        analyzer_errors=(),
        gate=GateVerdict(passed=passed, reasons=("PLB-SEC-002 (Blocker) at app.py:10",)),
        files_scanned=1,
        rules_loaded=20,
        semantic_node_count=semantic_nodes,
    )


def test_html_is_self_contained_offline() -> None:
    html = render_html(_result([_finding()]))
    # Inline CSS + inline JS are allowed (the sort/filter UI); EXTERNAL resources
    # are not — no `src=`, no CDN, no remote URLs.
    assert "src=" not in html
    assert "http://" not in html and "https://" not in html
    assert "cdn" not in html.lower()
    assert "<style>" in html  # CSS inline
    assert "<script>" in html  # JS inline (sort/filter), not external


def test_html_shows_readiness_and_pillars() -> None:
    html = render_html(_result([_finding()]))
    assert "Readiness Score" in html
    assert "Reliability" in html and "Security" in html


def test_html_is_deterministic() -> None:
    result = _result([_finding()])
    assert render_html(result) == render_html(result)


def test_html_na_when_no_agentic_code() -> None:
    html = render_html(_result([], semantic_nodes=0))
    assert "N/A" in html
    assert "No LLM/agent code detected" in html


def test_html_escapes_dynamic_text() -> None:
    # The report must not be its own XSS sink: a message with markup is escaped,
    # in both the cell and its data-attribute sort/search keys.
    html = render_html(_result([_finding(message="<script>alert(1)</script>")]))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_html_table_is_sortable_and_filterable() -> None:
    html = render_html(_result([_finding()]))
    assert "id=findings" in html  # the table the script targets
    assert "class=sortable" in html  # clickable column headers (all four)
    assert html.count("class=sortable") == 4  # Severity, Rule, Location, What & why
    assert "id=q" in html  # free-text filter input
    assert "sevchip" in html  # severity filter chip(s)
    assert "data-text=" in html and "data-sev=" in html  # per-row filter keys


def test_html_severity_sorts_by_rank_not_alphabetically() -> None:
    # A Major finding must sort below a Blocker even though "Major" > "Blocker"
    # alphabetically — the severity cell carries its numeric rank as the sort key.
    html = render_html(_result([_finding()]))
    assert f'data-sort="{Severity.BLOCKER.value}"' in html  # e.g. data-sort="50"
    assert Severity.BLOCKER.value > Severity.MAJOR.value  # rank order, not text


def test_html_no_toolbar_or_script_when_empty() -> None:
    # Nothing to sort/filter on a clean scan — no toolbar, no script noise.
    html = render_html(_result([], semantic_nodes=5, passed=True))
    assert "id=q" not in html and "<script>" not in html


def test_gate_verdict_rendered() -> None:
    assert "Quality Gate failed" in render_html(_result([_finding()], passed=False))
    assert "Quality Gate passed" in render_html(_result([], passed=True))


def test_gate_shows_blocking_count_not_redundant_reason_list() -> None:
    # The gate banner used to list every reason, duplicating the findings table.
    # Now it shows just the blocking count and points to the table below.
    html = render_html(_result([_finding()], passed=False))
    assert "1 blocking finding" in html
    assert "<ul class=why>" not in html  # the duplicated reason list is gone


def test_summary_strip_counts_findings_by_severity() -> None:
    html = render_html(_result([_finding(), _finding()]))
    assert "2 findings" in html
    assert "2 Blocker" in html  # both fixtures are Blocker severity


def test_pillar_bars_show_issue_counts() -> None:
    html = render_html(_result([_finding()]))  # one Security finding
    assert "1 issue" in html  # the Security pillar reports its count
    assert "no issues" in html  # pillars with nothing fired say so (not just "100")


def test_committed_example_report_is_not_stale() -> None:
    # CI tripwire. docs/examples/llm-sample-report.html is generated by hand from a
    # real repo scan (see docs/examples/README.md). If the HTML reporter gains a
    # structural feature (e.g. the sort/filter UI) the committed sample must be
    # regenerated, or it silently shows users an outdated report. Every structural
    # marker the CURRENT reporter emits must also appear in the committed sample.
    assert _EXAMPLE_REPORT.exists(), f"missing {_EXAMPLE_REPORT}"
    fresh = render_html(_result([_finding()]))
    example = _EXAMPLE_REPORT.read_text(encoding="utf-8")
    markers = (
        "id=findings",
        "class=sortable",
        "id=q",
        "sevchip",
        "<script>",
        "data-sev=",
        "data-sort=",
    )
    stale = [m for m in markers if m in fresh and m not in example]
    assert not stale, (
        f"docs/examples/llm-sample-report.html is stale (missing {stale}); "
        "regenerate it — see docs/examples/README.md."
    )


def test_branding_attributes_actaclad() -> None:
    # Product name stays "Plumbline"; ActaClad is the attribution.
    html = render_html(_result([_finding()]))
    assert "Plumbline" in html
    assert "by ActaClad" in html
