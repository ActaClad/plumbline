"""HTML reporter tests — offline, deterministic, escaped, scored (M7)."""

from __future__ import annotations

from plumbline.config import GateVerdict
from plumbline.engine import ScanResult
from plumbline.model import Confidence, Finding, Pillar, Severity
from plumbline.reporters.html import render_html


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
    # No network resources: no external scripts/styles/links, no CDN.
    assert "<script" not in html
    assert "src=" not in html
    assert "http://" not in html and "https://" not in html
    assert "<style>" in html  # CSS is inline


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
    # The report must not be its own XSS sink: a message with markup is escaped.
    html = render_html(_result([_finding(message="<script>alert(1)</script>")]))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_gate_verdict_rendered() -> None:
    assert "Quality Gate failed" in render_html(_result([_finding()], passed=False))
    assert "Quality Gate passed" in render_html(_result([], passed=True))


def test_summary_strip_counts_findings_by_severity() -> None:
    html = render_html(_result([_finding(), _finding()]))
    assert "2 findings" in html
    assert "2 Blocker" in html  # both fixtures are Blocker severity


def test_pillar_bars_show_issue_counts() -> None:
    html = render_html(_result([_finding()]))  # one Security finding
    assert "1 issue" in html  # the Security pillar reports its count
    assert "no issues" in html  # pillars with nothing fired say so (not just "100")


def test_branding_attributes_actaclad() -> None:
    # Product name stays "Plumbline"; ActaClad is the attribution.
    html = render_html(_result([_finding()]))
    assert "Plumbline" in html
    assert "by ActaClad" in html
