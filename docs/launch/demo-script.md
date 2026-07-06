# DRAFT — Launch demo script (60–90s terminal walkthrough)

> **Status: DRAFT — not yet published.** For the asciinema/terminal recording in the P2
> launch assets. Goal: in under 90 seconds, show a first-time viewer the *one*
> idea — Plumbline finds reliability defects, not security CVEs — on a real repo,
> with a real finding, a real gate, and a real fix. No slides. No narration track
> required; the on-screen comments carry it.
>
> **Recording notes:** record with `asciinema rec`, ~95 cols × 28 rows, a clean
> prompt (`PS1='$ '`). Target the GIF at ≤ 4 MB. The scan block below was
> **re-verified against the shipped 32-rule build** (`plumb 0.0.1`) on
> `simonw/llm @ 0d593ea` (2026-07-05): same 3 findings, same 93/100 — only the
> loaded-rule count moved 25 → 32. Re-verify if you record on a later Plumbline
> release, since `plumb` output can change as rules are added.

---

## Beat 0 — the hook (≈8s, on-screen title card or first comment line)

```
# Your AI agent didn't get hacked. It fell over.
# Security scanners tell you if your AI can be attacked.
# Plumbline tells you if it can survive production.  (a static analyzer for LLM/agent code)
# Let's point it at a real, well-built OSS tool — simonw/llm — cold.
```

## Beat 1 — install & scan (≈15s)

```bash
$ pip install actaclad-plumbline      # (pre-recorded; cut the install wait)
$ plumb scan ./llm
```

Expected (real) output — let it render, don't scroll past it:

```
  Critical/High   PLB-OUT-001  llm/default_plugins/openai_models.py:1027:35
  Critical/High   PLB-OUT-001  llm/default_plugins/openai_models.py:1143:35
  Major/Medium    PLB-OBS-001  llm/default_plugins/openai_models.py:961:26

3 findings across 49 file(s); 32 rule(s) loaded.  gate failed
Readiness Score: 93/100 · Reliability 80  Architecture 100  Harness 99  Security 100
```

```
# 3 findings on a genuinely good codebase. No noise, no 200-line FP dump.
# Note what it is NOT: no "possible secret", no CVE scare. These are reliability bugs.
```

## Beat 2 — the finding, in full (≈25s) — the payload of the demo

No extra command needed — the scan above already prints each finding's detail
inline (message → `why:` → `fix:`). Scroll up to the first OUT-001 and let it
sit on screen. This is the real CLI rendering:

```
  Critical/High PLB-OUT-001 llm/default_plugins/openai_models.py:1027:35
    LLM output is parsed with json.loads and no error handling; a malformed
    generation will raise and crash the request.
    why: `json.loads` on raw LLM output with no guard crashes on the first
    malformed generation.
    fix: Validate model output against a schema and handle parse failure
    (retry or fallback).
```

```
# What / where / why / how-to-fix — every finding, with a taint witness behind it.
# And note what's MISSING: no security-standard tag. This is a reliability defect.
# That's exactly why every existing AI scanner walks right past it.
```

## Beat 3 — the gate (≈12s)

```bash
$ echo $?        # exit code from the scan above
1
$ plumb scan ./llm --sarif results.sarif    # upload to the GitHub Security tab
```

```
# The Quality Gate failed (exit 1) on a High-confidence Critical — wire that into
# CI and a reliability regression can't merge. Deterministic: same code, same result.
# No network, no telemetry — analysis runs fully offline.
```

## Beat 3.5 — the shareable report (≈8s) — the money visual

```bash
$ plumb scan ./llm --open        # writes + opens a branded, self-contained HTML report
```

The branded report (Readiness 93/100, the four pillar bars, the gate banner) is
the most screenshot-able artifact Plumbline produces — put it on carousel slide 3
and in the blog. **Recording note:** the report opens in a *browser*, and terminal
recorders (VHS/asciinema) capture only the terminal. To show it in the video, do
one of:
- a **QuickTime screen recording** that runs `plumb scan ./llm --open` and lets the
  browser open the report (best — shows the CLI→report flow end to end); or
- generate it once (`plumb scan ./llm --html llm-report.html`) and drop a **still**
  into the blog / carousel.

Keep the terminal GIF (Beats 1–3, via `demo.tape`) as the deterministic core; the
report is the polished companion still/clip.

## Beat 4 — the close (≈10s)

```
# 32 rules today across Reliability, Architecture, Harness, Security —
# the differentiated ones (reliability + architecture) lead.
# Open source, Apache-2.0. Add a rule in an afternoon.
#
#   pip install actaclad-plumbline   →   cd your-agent && plumb scan
#
# github.com/ActaClad/plumbline
```

---

## Cutting it to 60s

Drop Beat 3's SARIF line and the `--sarif` flourish; keep install → scan →
one finding in full → gate-failed exit code → CTA. The single non-negotiable
beat is **Beat 2** — the viewer must see one real, specific, *reliability* finding
with its why-it-matters and its fix. That is the whole pitch.

## What NOT to do

- Don't scan a contrived repo stuffed with bugs — the credibility comes from a
  *recognizable, well-engineered* tool scoring 93 with a few real findings.
- Don't claim "finds all your bugs." Show three, honestly.
- Don't show a finding whose fix you can't defend on camera.
