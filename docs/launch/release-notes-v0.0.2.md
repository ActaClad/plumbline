# Plumbline v0.0.2

> **Draft — GitHub Release body for tag `v0.0.2`.** Paste into the release on
> github.com/ActaClad/plumbline (or `gh release create v0.0.2 -F` this file).
> Publishing triggers `publish.yml` → trusted publishing to PyPI (0.0.2 is a new
> version, so this is a real upload, not a skip). Numbers are from `CHANGELOG.md`.

First point release after launch. Two things drove it, both found by pointing
Plumbline at real code: a whole stack we couldn't see, and a report that buried
its own signal. Detection stays deterministic — no rule gating changed.

```bash
pipx install --upgrade actaclad-plumbline   # or: uv tool upgrade actaclad-plumbline
```

## New: Google Gemini support

Plumbline now understands the **`google-genai`** SDK — `genai.Client(...)`, the
sync and async (`.aio`) `models.generate_content` (and its streaming form),
Gemini **Live** `connect`, and `embed_content` — plus the legacy
`google.generativeai` SDK. Before this, an entire class of apps was invisible: a
real production Gemini voice-agent scanned to `Readiness N/A` because every model
call went through an unrecognized SDK. It now scores 99/100 and surfaces real
reliability findings.

Precision-first: Gemini nests its generation config inside
`config=GenerateContentConfig(...)` and the client timeout in `http_options`, so
those aren't resolvable at the call site yet — the adapter marks them `UNKNOWN`
(not `ABSENT`), and the High-confidence RES/COST/MDL rules stay silent rather than
false-positive. Model output still seeds taint (OUT-001/002), and the app is
scored.

## New: recurring-finding aggregation in the report

A rule that legitimately fires many times in a file used to produce a wall of
near-identical rows (real case: **31× GOV-002** email-in-log across one auth
service). The HTML report now **collapses findings that share rule + file +
message into a single row** — *"N sites"* with every line listed, so each stays
fixable. This is **presentation only**: SARIF, JSON, the Quality Gate, the
summary strip, and pillar counts still see every finding, so *"N findings"* stays
honest.

## Changed: the report wears the brand

The HTML report is rebranded to the ActaClad palette — near-black + gold in dark
mode, warm cream/paper + gold in light — with the gold plumb-line mark and a
faint AC-hexagon watermark. Pass/fail still reads at a glance (semantic
green/gold/red). Determinism and the fully-offline guarantee are unchanged.

## Also

- README: an install note (pipx / `uv tool install`, Python 3.11+) that preempts
  the two most common first-run errors, a problem-first TL;DR, and the
  generation-time skill pack surfaced up front.
- Real-repo validation grows to **10 repos** — the Gemini voice-agent (recall gap
  → adapter) and the Backsie backend (signal-to-noise → aggregation) — in
  [`benchmark/real-repos.md`](../../benchmark/real-repos.md).

**Full detail:** [`CHANGELOG.md`](../../CHANGELOG.md) ·
**Repo:** github.com/ActaClad/plumbline
