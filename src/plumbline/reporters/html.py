"""HTML report reporter (architecture.md §6, M7).

A single self-contained file: inline CSS and inline vanilla JS, **no CDN, no
external resources** — it renders fully offline. Shows a branded header, a
scan-metadata strip, the Readiness Score, the pillar breakdown, the gate verdict,
and a findings table that the reader can **sort** (click any column header —
Severity sorts by severity rank, not alphabetically), **filter** (free-text
search + severity chips), and expand per finding to read the **remediation**
("how to fix") — all client-side. A light/dark **theme toggle** and a print
stylesheet make it presentable on screen and as an exported PDF.

Deterministic and byte-reproducible (no timestamps; findings rendered in
`finding_sort_key` order; the JS only re-orders/reveals live DOM on interaction,
never the emitted bytes — ADR-0002 D3). All dynamic text is HTML-escaped,
including data-attribute values — the report must never be its own XSS sink
(cf. SEC-006); the script only reads `textContent`/`dataset` and toggles
attributes, never injects markup.
"""

from __future__ import annotations

import html
from collections.abc import Iterable, Mapping
from importlib.metadata import PackageNotFoundError, version

from ..engine import ScanResult
from ..model import Finding, Pillar, Severity, finding_sort_key
from ..scoring import Scores, compute_scores

# Severities shown in the summary strip, worst-first.
_SEV_ORDER: tuple[Severity, ...] = (
    Severity.BLOCKER,
    Severity.CRITICAL,
    Severity.MAJOR,
    Severity.MINOR,
    Severity.INFO,
)

_SEV_CLASS: dict[Severity, str] = {
    Severity.BLOCKER: "blocker",
    Severity.CRITICAL: "critical",
    Severity.MAJOR: "major",
    Severity.MINOR: "minor",
    Severity.INFO: "info",
}

# Inline plumb-line mark (a beam, a string, and a plumb bob). Monochrome via
# currentColor so it inherits the accent — no external image, offline-safe.
_LOGO = (
    "<svg class=logo viewBox='0 0 24 24' width=26 height=26 fill=none "
    "stroke=currentColor stroke-width=1.7 stroke-linecap=round stroke-linejoin=round "
    "aria-hidden=true><path d='M4 5h16'/><path d='M12 5v10'/><path d='M12 15l3.2 4.5H8.8Z'/></svg>"
)

_STYLE = """\
/* ActaClad brand — dark (default): near-black + gold. Semantic ok/warn/bad stay
   green/gold/red so pass/fail reads at a glance (info design ≠ brand accent). */
:root { --bg:#0d0d0d; --card:#1a1610; --fg:#ede6d6; --muted:#9a9488; --line:#2c2620;
  --accent:#d9ae5a; --ok:#5cb87a; --warn:#c8951e; --bad:#e5735b;
  --okbg:rgba(92,184,122,.15); --warnbg:rgba(200,149,30,.16); --badbg:rgba(229,115,91,.16);
  --chip:#241f16; }
/* light: warm cream/paper + gold, matching actaclad.com's light mode. */
:root[data-theme=light] { --bg:#f5f1e8; --card:#fffdf8; --fg:#2a241a; --muted:#6f685a;
  --line:#e3dccc; --accent:#a9781a; --ok:#2f8a52; --warn:#9a6f10; --bad:#c14a35;
  --okbg:rgba(47,138,82,.12); --warnbg:rgba(154,111,16,.14); --badbg:rgba(193,74,53,.12);
  --chip:#efe8d8; }
* { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--fg);
  font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif; }
.wrap { max-width:960px; margin:0 auto; padding:32px 20px; }
.brand { display:flex; align-items:center; gap:10px; margin:0 0 2px; }
.brand .logo { color:var(--accent); flex:none; }
h1 { font-size:20px; margin:0; letter-spacing:.2px; } .brand .sp { flex:1; }
.themebtn { cursor:pointer; border:1px solid var(--line); background:var(--card);
  color:var(--muted); border-radius:8px; padding:4px 10px; font-size:12px; font-weight:600; }
.themebtn:hover { color:var(--fg); }
.sub { color:var(--muted); margin:0 0 14px; }
.meta { display:flex; flex-wrap:wrap; gap:6px 18px; color:var(--muted); font-size:12px;
  padding:0 0 18px; border-bottom:1px solid var(--line); margin-bottom:20px; }
.meta b { color:var(--fg); font-weight:600; }
.hero { display:flex; gap:28px; align-items:center; background:var(--card);
  border:1px solid var(--line); border-radius:12px; padding:24px; margin-bottom:20px; }
.score { font-size:52px; font-weight:700; line-height:1; }
.score small { font-size:18px; color:var(--muted); font-weight:400; }
.pillars { flex:1; display:grid; gap:10px; }
.pillar { display:grid; grid-template-columns:170px 1fr 40px 84px; gap:10px; align-items:center; }
.pillar .count { color:var(--muted); font-size:12px; text-align:right; }
.pillar .count.has { color:var(--fg); }
.bar { height:8px; background:var(--line); border-radius:4px; overflow:hidden; }
.bar > i { display:block; height:100%; }
.summary { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:baseline;
  margin-bottom:16px; color:var(--muted); font-size:13px; }
.summary .total { color:var(--fg); font-size:15px; font-weight:700; }
.summary .pill { display:inline-block; padding:1px 8px; border-radius:10px;
  background:var(--chip); }
.gate { padding:12px 16px; border-radius:8px; margin-bottom:20px; font-weight:600; }
.gate.pass { background:var(--okbg); color:var(--ok); }
.gate.fail { background:var(--badbg); color:var(--bad); }
table { width:100%; border-collapse:collapse; background:var(--card);
  border:1px solid var(--line); border-radius:12px; overflow:hidden; }
th,td { text-align:left; padding:10px 12px; border-bottom:1px solid var(--line);
  vertical-align:top; } th { color:var(--muted); font-weight:600; font-size:12px;
  text-transform:uppercase; } tr:last-child td { border-bottom:none; }
.tag { display:inline-block; padding:1px 8px; border-radius:10px; font-size:12px;
  font-weight:600; } .blocker,.critical { background:var(--badbg); color:var(--bad); }
.major { background:var(--warnbg); color:var(--warn); }
.minor,.info { background:var(--chip); color:var(--muted); }
.loc { color:var(--muted); font-family:ui-monospace,monospace; font-size:12px; }
.msg { color:var(--fg); } .why { color:var(--muted); font-size:13px; }
.fix { margin-top:8px; } .fix > summary { cursor:pointer; color:var(--accent);
  font-size:12px; font-weight:600; list-style:none; }
.fix > summary::-webkit-details-marker { display:none; }
.fix > summary::before { content:'▸ '; } .fix[open] > summary::before { content:'▾ '; }
.fix pre { white-space:pre-wrap; word-break:break-word; margin:8px 0 2px;
  padding:10px 12px; background:var(--bg); border:1px solid var(--line);
  border-radius:8px; font:12px/1.5 ui-monospace,monospace; color:var(--fg); }
.empty { color:var(--muted); padding:24px; text-align:center; }
.toolbar { display:flex; flex-wrap:wrap; gap:8px 12px; align-items:center;
  margin-bottom:10px; }
.toolbar input { flex:1 1 220px; min-width:180px; background:var(--card);
  border:1px solid var(--line); border-radius:8px; color:var(--fg);
  padding:7px 10px; font-size:13px; }
.sevfilter { display:flex; gap:6px; flex-wrap:wrap; }
.sevchip { cursor:pointer; border:1px solid var(--line); background:var(--chip);
  color:var(--fg); border-radius:10px; padding:2px 10px; font-size:12px;
  font-weight:600; } .sevchip.off { opacity:.4; }
#visct { color:var(--muted); font-size:12px; margin-left:auto; }
th.sortable { cursor:pointer; user-select:none; } th.sortable:hover { color:var(--fg); }
.arrow { font-size:10px; color:var(--fg); }
.footer { margin-top:28px; padding-top:16px; border-top:1px solid var(--line);
  color:var(--muted); font-size:12px; line-height:1.6; }
.footer b { color:var(--fg); font-weight:600; }
@media print {
  :root { --bg:#fff; --card:#fff; --fg:#111; --muted:#555; --line:#ccc; }
  body { background:#fff; } .themebtn, .toolbar { display:none; }
  .hero, table { break-inside:avoid; } tr { break-inside:avoid; }
  .fix pre { display:block !important; } .fix[open] > summary::before,
  .fix > summary::before { content:''; } .fix > summary { color:var(--muted); }
}
"""


def _report_version() -> str:
    try:
        return version("actaclad-plumbline")
    except PackageNotFoundError:  # not installed as a dist (e.g. source checkout)
        return ""


def render_html(result: ScanResult) -> str:
    scores = compute_scores(result.findings, result.semantic_node_count)
    pillar_counts = _count_by_pillar(result.findings)
    parts = [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>",
        "<title>Plumbline report</title><style>",
        _STYLE,
        "</style></head><body><div class=wrap>",
        f"<div class=brand>{_LOGO}<h1>Plumbline</h1><span class=sp></span>"
        "<button class=themebtn id=theme type=button>Light</button></div>",
        "<p class=sub>Reliability &amp; architecture analysis for agentic systems · "
        "by ActaClad</p>",
        _meta(result),
        _hero(scores, pillar_counts),
        _gate(result),
        _summary(result.findings),
        _toolbar(result.findings),
        _findings_table(result.findings),
        _footer(),
        "</div>",
        _THEME_SCRIPT,
        _SCRIPT if result.findings else "",
        "</body></html>",
    ]
    return "".join(parts) + "\n"


def _count_by_pillar(findings: Iterable[Finding]) -> dict[Pillar, int]:
    counts: dict[Pillar, int] = dict.fromkeys(Pillar, 0)
    for f in findings:
        counts[f.pillar] += 1
    return counts


def _count_by_severity(findings: Iterable[Finding]) -> dict[Severity, int]:
    counts: dict[Severity, int] = dict.fromkeys(Severity, 0)
    for f in findings:
        counts[f.severity] += 1
    return counts


def write_html(result: ScanResult, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_html(result))


def _meta(result: ScanResult) -> str:
    total = len(result.findings)
    files = f"<b>{result.files_scanned}</b> file{'' if result.files_scanned == 1 else 's'}"
    rules = f"<b>{result.rules_loaded}</b> rule{'' if result.rules_loaded == 1 else 's'} run"
    finds = f"<b>{total}</b> finding{'' if total == 1 else 's'}"
    ver = _report_version()
    version_span = f"<span>Plumbline v{html.escape(ver)}</span>" if ver else ""
    return (
        f"<div class=meta><span>{files} scanned</span><span>{rules}</span>"
        f"<span>{finds}</span>{version_span}</div>"
    )


def _hero(scores: Scores, counts: Mapping[Pillar, int]) -> str:
    if not scores.applicable:
        return (
            "<div class=hero><div class=score>N/A</div>"
            "<div class=pillars><div class=why>No LLM/agent code detected — scoring "
            "does not apply (ADR-0008 D3).</div></div></div>"
        )
    bars = "".join(_pillar_bar(p, scores.pillars[p], counts.get(p, 0)) for p in Pillar)
    return (
        f"<div class=hero><div><div class=score>{scores.readiness}<small>/100</small></div>"
        "<div class=why>Readiness Score</div></div>"
        f"<div class=pillars>{bars}</div></div>"
    )


def _pillar_bar(pillar: Pillar, value: int, count: int) -> str:
    color = _score_color(value)
    label = html.escape(pillar.display)
    issues = "no issues" if count == 0 else f"{count} issue{'' if count == 1 else 's'}"
    cls = "count" if count == 0 else "count has"
    return (
        f"<div class=pillar><span>{label}</span>"
        f"<span class=bar><i style='width:{value}%;background:{color}'></i></span>"
        f"<span>{value}</span>"
        f"<span class='{cls}'>{issues}</span></div>"
    )


def _summary(findings: Iterable[Finding]) -> str:
    findings = list(findings)
    total = len(findings)
    if total == 0:
        return ""
    sev_counts = _count_by_severity(findings)
    noun = "finding" if total == 1 else "findings"
    pills = "".join(
        f"<span class=pill>{sev_counts[s]} {html.escape(s.label)}</span>"
        for s in _SEV_ORDER
        if sev_counts[s]
    )
    return f"<div class=summary><span class=total>{total} {noun}</span>{pills}</div>"


def _score_color(value: int) -> str:
    if value >= 80:
        return "var(--ok)"
    if value >= 50:
        return "var(--warn)"
    return "var(--bad)"


def _gate(result: ScanResult) -> str:
    if result.gate.passed:
        return "<div class='gate pass'>✓ Quality Gate passed</div>"
    # The verdict is the product (CLAUDE.md §1.6); the per-finding reasons used to
    # duplicate the table below, so we show only the blocking count and point down.
    n = len(result.gate.reasons)
    noun = "finding" if n == 1 else "findings"
    return (
        f"<div class='gate fail'>✗ Quality Gate failed — {n} blocking {noun} "
        "(Blockers and High-confidence Criticals), listed below</div>"
    )


def _footer() -> str:
    # Attribution + standards only — no hyperlink (the report is strictly offline;
    # an external URL would break the no-network guarantee the tests enforce) and
    # no commercial/upsell line: the OSS artifact carries the project's identity,
    # not a sales pitch.
    return (
        "<div class=footer><b>Plumbline</b> — the open-source reliability &amp; "
        "architecture analyzer for LLM &amp; agentic systems, by <b>ActaClad</b>. "
        "Detection is deterministic and fully offline. Findings map to OWASP LLM &amp; "
        "Agentic Top&nbsp;10, NIST AI RMF, and CWE. <em>The craft of intelligence.</em></div>"
    )


_HEADERS: tuple[str, ...] = ("Severity", "Rule", "Location", "What &amp; why")


def _toolbar(findings: Iterable[Finding]) -> str:
    findings = list(findings)
    if not findings:
        return ""
    present = [s for s in _SEV_ORDER if any(f.severity is s for f in findings)]
    chips = "".join(
        f'<button class=sevchip data-sev="{html.escape(s.label)}">{html.escape(s.label)}</button>'
        for s in present
    )
    return (
        "<div class=toolbar>"
        '<input id=q type=search placeholder="Filter findings…" aria-label="Filter findings">'
        f"<span class=sevfilter>{chips}</span>"
        "<span id=visct class=why></span>"
        "</div>"
    )


def _findings_table(findings: Iterable[Finding]) -> str:
    rows = sorted(findings, key=finding_sort_key)
    if not rows:
        return "<table><tr><td class=empty>No findings.</td></tr></table>"
    head = "".join(f"<th class=sortable>{h}<span class=arrow></span></th>" for h in _HEADERS)
    body = "".join(_row(f) for f in rows)
    return f"<table id=findings><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _row(f: Finding) -> str:
    sev = _SEV_CLASS.get(f.severity, "info")
    col = f":{f.column + 1}" if f.column is not None else ""
    loc = f"{f.file}:{f.line}{col}"
    std = f" · {html.escape(', '.join(f.standards))}" if f.standards else ""
    # Per-row searchable text + per-cell sort keys. Severity sorts by its numeric
    # rank (Blocker=50 … Info=10); location pads the line so it orders numerically
    # within a file. All attribute values are escaped (SEC-006 — no self-XSS).
    searchable = " ".join(
        [f.rule_id, loc, f.message, f.why_it_matters, f.remediation, *f.standards]
    ).lower()
    loc_key = f"{f.file}:{f.line:08d}".lower()
    return (
        f'<tr data-sev="{html.escape(f.severity.label)}" data-text="{html.escape(searchable)}">'
        f'<td data-sort="{f.severity.value}"><span class="tag {sev}">{f.severity.label}</span>'
        f"<div class=why>{f.confidence.label}</div></td>"
        f'<td data-sort="{html.escape(f.rule_id.lower())}">'
        f"<strong>{html.escape(f.rule_id)}</strong>{std}</td>"
        f'<td class=loc data-sort="{html.escape(loc_key)}">{html.escape(loc)}</td>'
        f'<td data-sort="{html.escape(f.message.lower())}">'
        f"<div class=msg>{html.escape(f.message)}</div>"
        f"<div class=why>{html.escape(f.why_it_matters)}</div>"
        f"{_fix(f)}</td></tr>"
    )


def _fix(f: Finding) -> str:
    if not f.remediation.strip():
        return ""
    return (
        "<details class=fix><summary>How to fix</summary>"
        f"<pre>{html.escape(f.remediation.rstrip())}</pre></details>"
    )


# Theme toggle — emitted always (works with zero findings). Flips the root
# data-theme between dark/light and relabels the button. No storage, no network.
_THEME_SCRIPT = """\
<script>
(function () {
  var btn = document.getElementById('theme');
  if (!btn) return;
  var root = document.documentElement;
  function set(t) {
    root.setAttribute('data-theme', t);
    btn.textContent = (t === 'light') ? 'Dark' : 'Light';
  }
  set('dark');
  btn.addEventListener('click', function () {
    set(root.getAttribute('data-theme') === 'light' ? 'dark' : 'light');
  });
})();
</script>"""

# Inline, dependency-free. Reads dataset/textContent and toggles display + reorders
# rows; never injects markup (the cells are already escaped server-side).
_SCRIPT = """\
<script>
(function () {
  var tbl = document.getElementById('findings');
  if (!tbl) return;
  var body = tbl.tBodies[0];
  var rows = Array.prototype.slice.call(body.rows);
  var q = document.getElementById('q');
  var ct = document.getElementById('visct');
  var off = {};

  function apply() {
    var term = (q && q.value || '').toLowerCase();
    var vis = 0;
    rows.forEach(function (r) {
      var show = (!term || r.dataset.text.indexOf(term) >= 0) && !off[r.dataset.sev];
      r.style.display = show ? '' : 'none';
      if (show) vis++;
    });
    if (ct) ct.textContent = vis + ' of ' + rows.length + ' shown';
  }

  if (q) q.addEventListener('input', apply);
  Array.prototype.forEach.call(document.querySelectorAll('.sevchip'), function (c) {
    c.addEventListener('click', function () {
      var s = c.dataset.sev;
      off[s] = !off[s];
      c.classList.toggle('off', off[s]);
      apply();
    });
  });

  var dir = {};
  var ths = tbl.tHead.rows[0].cells;
  Array.prototype.forEach.call(ths, function (th, i) {
    th.addEventListener('click', function () {
      var d = dir[i] = (dir[i] === 1) ? -1 : 1;
      var numeric = rows.every(function (r) {
        var v = r.cells[i].dataset.sort;
        return v !== undefined && v !== '' && !isNaN(v);
      });
      rows.slice().sort(function (a, b) {
        var av = a.cells[i].dataset.sort || '', bv = b.cells[i].dataset.sort || '';
        var c = numeric ? (parseFloat(av) - parseFloat(bv)) : av.localeCompare(bv);
        return d * c;
      }).forEach(function (r) { body.appendChild(r); });
      Array.prototype.forEach.call(ths, function (h) {
        var a = h.querySelector('.arrow'); if (a) a.textContent = '';
      });
      var arr = th.querySelector('.arrow'); if (arr) arr.textContent = d > 0 ? ' ▲' : ' ▼';
    });
  });

  apply();
})();
</script>"""
