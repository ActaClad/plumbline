# Changelog

All notable changes to Plumbline are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/); this project uses semantic
versioning once it reaches 1.0.

## [Unreleased] — v0.1 development

The first end-to-end implementation: a deterministic reliability/architecture
analyzer for LLM & agentic Python, built substrate-first across M0–M8 plus a
hardening pass. **20 rules across all four pillars** (13 High-confidence, each
with a measured precision in `/benchmark`).

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
  OUT-001 (unguarded JSON parse), COST-001 (no max_tokens), MDL-001 (scattered
  model literals).
- **Architecture:** AGT-001/002 (agent-loop cap / termination, one detector
  across three frameworks), TOOL-001 (untyped tool).
- **Harness:** EVAL-001/003 (no eval suite / no CI eval gate), OBS-001 (no
  tracing) — the "flying blind" rules.
- **Security:** SEC-002/003/004/005/006 (eval/exec, shell, secret, SQLi, XSS)
  High; SEC-007 (SSRF) + GOV-001/002 (PII, logging) advisory; taint findings
  carry source→sink SARIF codeFlows.

### Reporters, gate, scoring
- Quality Gate (CI mechanism) + the Readiness Score (0–100 dashboard, ADR-0008,
  never the gate). N/A when no agentic code.
- CLI, SARIF 2.1.0 (schema-validated, codeFlows), JSON, and a self-contained
  offline HTML report. Baselines + inline suppressions.

### Distribution & remediation
- `plumb export-skills` — the rule set as a generation-time prevention pack
  (prevention, never the gate; ADR-0011).
- Optional AI remediation enrichment behind a tested determinism firewall — the
  LLM rewrites only remediation text, never detection (ADR-0015).

### Hardening
- Dogfood self-scan in CI; robustness battery (gnarly + malformed Python);
  real-world false-positive audit; packaging verification (clean-venv wheel
  install); linear-scaling performance check.
