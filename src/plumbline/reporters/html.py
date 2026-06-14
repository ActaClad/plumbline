"""HTML report reporter (architecture.md §6, M7).

A single self-contained file: inline CSS, no CDN, no JavaScript — it renders
offline. Shows the Readiness Score, the pillar breakdown, the gate verdict, and a
findings table. Deterministic and byte-reproducible (no timestamps, findings
sorted, ADR-0002 D3). All dynamic text is HTML-escaped — the report must never be
its own XSS sink (cf. SEC-006).
"""

from __future__ import annotations

import html
from collections.abc import Iterable

from ..engine import ScanResult
from ..model import Finding, Pillar, Severity, finding_sort_key
from ..scoring import Scores, compute_scores

_SEV_CLASS: dict[Severity, str] = {
    Severity.BLOCKER: "blocker",
    Severity.CRITICAL: "critical",
    Severity.MAJOR: "major",
    Severity.MINOR: "minor",
    Severity.INFO: "info",
}

_STYLE = """\
:root { --bg:#0f1419; --card:#1a2029; --fg:#e6e6e6; --muted:#8a94a6; --line:#2a3340;
  --ok:#3fb950; --warn:#d29922; --bad:#f85149; }
* { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--fg);
  font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif; }
.wrap { max-width:960px; margin:0 auto; padding:32px 20px; }
h1 { font-size:20px; margin:0 0 4px; } .sub { color:var(--muted); margin:0 0 24px; }
.hero { display:flex; gap:28px; align-items:center; background:var(--card);
  border:1px solid var(--line); border-radius:12px; padding:24px; margin-bottom:20px; }
.score { font-size:52px; font-weight:700; line-height:1; }
.score small { font-size:18px; color:var(--muted); font-weight:400; }
.pillars { flex:1; display:grid; gap:10px; }
.pillar { display:grid; grid-template-columns:160px 1fr 40px; gap:10px; align-items:center; }
.bar { height:8px; background:var(--line); border-radius:4px; overflow:hidden; }
.bar > i { display:block; height:100%; }
.gate { padding:12px 16px; border-radius:8px; margin-bottom:20px; font-weight:600; }
.gate.pass { background:rgba(63,185,80,.15); color:var(--ok); }
.gate.fail { background:rgba(248,81,73,.15); color:var(--bad); }
table { width:100%; border-collapse:collapse; background:var(--card);
  border:1px solid var(--line); border-radius:12px; overflow:hidden; }
th,td { text-align:left; padding:10px 12px; border-bottom:1px solid var(--line);
  vertical-align:top; } th { color:var(--muted); font-weight:600; font-size:12px;
  text-transform:uppercase; } tr:last-child td { border-bottom:none; }
.tag { display:inline-block; padding:1px 8px; border-radius:10px; font-size:12px;
  font-weight:600; } .blocker,.critical { background:rgba(248,81,73,.15); color:var(--bad); }
.major { background:rgba(210,153,34,.15); color:var(--warn); }
.minor,.info { background:rgba(138,148,166,.15); color:var(--muted); }
.loc { color:var(--muted); font-family:ui-monospace,monospace; font-size:12px; }
.msg { color:var(--fg); } .why { color:var(--muted); font-size:13px; }
.empty { color:var(--muted); padding:24px; text-align:center; }
"""


def render_html(result: ScanResult) -> str:
    scores = compute_scores(result.findings, result.semantic_node_count)
    parts = [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>",
        "<title>Plumbline report</title><style>",
        _STYLE,
        "</style></head><body><div class=wrap>",
        "<h1>Plumbline</h1>",
        "<p class=sub>Reliability &amp; architecture analysis for agentic systems</p>",
        _hero(scores),
        _gate(result),
        _findings_table(result.findings),
        "</div></body></html>",
    ]
    return "".join(parts) + "\n"


def write_html(result: ScanResult, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_html(result))


def _hero(scores: Scores) -> str:
    if not scores.applicable:
        return (
            "<div class=hero><div class=score>N/A</div>"
            "<div class=pillars><div class=why>No LLM/agent code detected — scoring "
            "does not apply (ADR-0008 D3).</div></div></div>"
        )
    bars = "".join(_pillar_bar(p, scores.pillars[p]) for p in Pillar)
    return (
        f"<div class=hero><div><div class=score>{scores.readiness}<small>/100</small></div>"
        "<div class=why>Readiness Score</div></div>"
        f"<div class=pillars>{bars}</div></div>"
    )


def _pillar_bar(pillar: Pillar, value: int) -> str:
    color = _score_color(value)
    label = html.escape(pillar.display)
    return (
        f"<div class=pillar><span>{label}</span>"
        f"<span class=bar><i style='width:{value}%;background:{color}'></i></span>"
        f"<span>{value}</span></div>"
    )


def _score_color(value: int) -> str:
    if value >= 80:
        return "var(--ok)"
    if value >= 50:
        return "var(--warn)"
    return "var(--bad)"


def _gate(result: ScanResult) -> str:
    if result.gate.passed:
        return "<div class='gate pass'>✓ Quality Gate passed</div>"
    reasons = "".join(f"<li>{html.escape(r)}</li>" for r in result.gate.reasons)
    return f"<div class='gate fail'>✗ Quality Gate failed</div><ul class=why>{reasons}</ul>"


def _findings_table(findings: Iterable[Finding]) -> str:
    rows = sorted(findings, key=finding_sort_key)
    if not rows:
        return "<table><tr><td class=empty>No findings.</td></tr></table>"
    body = "".join(_row(f) for f in rows)
    return (
        "<table><thead><tr><th>Severity</th><th>Rule</th><th>Location</th>"
        f"<th>What &amp; why</th></tr></thead><tbody>{body}</tbody></table>"
    )


def _row(f: Finding) -> str:
    sev = _SEV_CLASS.get(f.severity, "info")
    col = f":{f.column + 1}" if f.column is not None else ""
    std = f" · {html.escape(', '.join(f.standards))}" if f.standards else ""
    return (
        f"<tr><td><span class='tag {sev}'>{f.severity.label}</span>"
        f"<div class=why>{f.confidence.label}</div></td>"
        f"<td><strong>{html.escape(f.rule_id)}</strong>{std}</td>"
        f"<td class=loc>{html.escape(f.file)}:{f.line}{col}</td>"
        f"<td><div class=msg>{html.escape(f.message)}</div>"
        f"<div class=why>{html.escape(f.why_it_matters)}</div></td></tr>"
    )
