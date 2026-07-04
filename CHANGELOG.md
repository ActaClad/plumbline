# Changelog

All notable changes to Plumbline are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/); this project uses semantic
versioning once it reaches 1.0.

## [Unreleased]

_Nothing yet._

## [0.0.1] — 2026-07-04

Initial public release: a deterministic reliability/architecture analyzer for
LLM & agentic Python, built substrate-first across M0–M8 plus a launch-hardening
pass. **32 rules across all four pillars** (12 High-confidence/gating,
20 Medium/advisory), weighted to the differentiated wedge — Reliability and
Architecture lead, ahead of Security; the full 60-rule taxonomy in the catalog is
the published contributor roadmap. High-confidence rules carry a measured
precision in `/benchmark`; advisory rules graduate to High only after a real-repo
precision pass.

### Engine & substrate
- Deterministic AST + taint/dataflow core (stdlib `ast`); no network, clock, or
  randomness in the detection path. Byte-reproducible output.
- Framework adapters (raw OpenAI/Anthropic SDK, LangChain/LangGraph, CrewAI) →
  a normalized semantic-tag vocabulary, so one rule covers many frameworks.
- **Cross-module client detection** (ADR-0016): a centralized client imported
  across modules is analyzed, not missed.
- Tri-state attribute resolution (`Known`/`ABSENT`/`UNKNOWN`) as the precision
  mechanism — High rules never fire on `UNKNOWN`.

### Rules (pillars: Reliability → Architecture → Harness → Security)
- **Reliability:** RES-001/002/005 (timeout, retries, swallowed errors),
  OUT-001 (unguarded JSON parse) High; OUT-002 (output as control flow),
  MDL-002 (deprecated/sunset model id, ADR-0017), MDL-003 (high temperature on a
  tool-calling path) advisory; COST-001 (no max_tokens) High; MDL-001 (scattered
  model literals) advisory.
- **Architecture:** AGT-001/002 (agent-loop cap / termination, one detector
  across three frameworks), TOOL-001 (untyped tool) High; TOOL-003 (tool with no
  error handling) and PRM-003 (no system prompt — opens the PRM category) advisory.
- **Harness:** EVAL-001/003 (no eval suite / no CI eval gate), OBS-001 (no
  tracing) — the "flying blind" rules.
- **Security:** SEC-002/003/005/006 (eval/exec, shell, SQLi, XSS) High; SEC-004
  (hardcoded secret) downgraded to advisory after real-repo validation; SEC-007
  (SSRF) + GOV-001/002 (PII, logging) advisory; taint findings carry source→sink
  SARIF codeFlows.
- **Reasoning-model configuration (ADR-0018):** MDL-006 (removed sampling param
  — `temperature`/`top_p`/`top_k` — on a reasoning model), MDL-007 (Anthropic
  extended-thinking budget out of range), MDL-008 (OpenAI reasoning model uses
  `max_tokens` instead of `max_completion_tokens`) — each a guaranteed HTTP 400,
  keyed on curated static model tables.
- **RES-010** (streamed response not used as a context manager → leaked HTTP
  connection). **MCP category** (new): MCP-001 (remote MCP server with no auth),
  MCP-003 (over-broad/wildcard OAuth scopes). **AGT-008** (AutoGen team with no
  turn cap or termination condition).

### Reporters, gate, scoring
- Quality Gate (CI mechanism) + the Readiness Score (0–100 dashboard, ADR-0008,
  never the gate). N/A when no agentic code.
- CLI, SARIF 2.1.0 (schema-validated, codeFlows), JSON, and a self-contained
  offline HTML report — branded (plumb-line mark, scan-metadata strip, expandable
  remediation, light/dark toggle, print/PDF stylesheet). `plumb scan --open`
  writes and opens a shareable report. Baselines + inline suppressions.

### Distribution & remediation
- `plumb export-skills` — the rule set as a generation-time prevention pack
  (prevention, never the gate; ADR-0011).
- Optional AI remediation enrichment behind a tested determinism firewall — the
  LLM rewrites only remediation text, never detection (ADR-0015).

### Fixes (launch hardening)
- EVAL-003 recognizes `rye test` (no longer false-flags Rye-based CI).
- Makefile is Windows-portable (OS-detected venv layout; portable `help`/`clean`).
- Config file reads use explicit `encoding="utf-8"` (no `UnicodeDecodeError` on
  non-UTF-8 default locales).
- COST-001 recognizes `max_completion_tokens` / `max_output_tokens` as output
  caps — no longer false-positives on correctly-bounded reasoning-model calls.

### Hardening
- Dogfood self-scan in CI; robustness battery (gnarly + malformed Python);
  real-world false-positive audit; packaging verification (clean-venv wheel
  install); linear-scaling performance check.
