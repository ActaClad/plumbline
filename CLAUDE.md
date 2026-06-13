# CLAUDE.md — Plumbline Project Constitution

> **This file is read at the start of every Claude Code session. It is the
> single source of behavioral truth for building Plumbline. When any other
> instruction conflicts with this file, this file wins. When this file is
> silent, consult `/docs/adr` (decisions) and `/docs/specs` (component specs).**

---

## 0. What Plumbline is (in one paragraph)

Plumbline is an open-source **static analyzer for LLM and agentic AI applications**.
It is **not a linter** in the style-checking sense — it is a reliability and
architecture analyzer. It answers the question *"will this agentic system fall
over in production?"* by statically detecting reliability, architecture,
harness-engineering, and security defects in AI/agent code. A plumb line is the
craftsman's oldest instrument for checking whether a structure is built true;
this tool does the same for agentic systems. It is built by **ActaClad** and is
the design-time companion to ActaClad's runtime trust platform, **AgentGuard**.

---

## 1. Non-negotiable principles

These are invariants. Do not violate them. If a task seems to require violating
one, stop and surface the conflict rather than proceeding.

1. **Detection is deterministic. Remediation may use AI.**
   The rule engine is pure static analysis (AST + dataflow). Running Plumbline
   twice on the same code MUST produce identical findings. An LLM may ONLY be
   used to generate human-readable fix/remediation text — NEVER to decide
   whether a finding exists. No network calls in the detection path.
   Rule knowledge may also be exported as a generation-time skill-pack to
   *prevent* defects at authoring time (ADR-0011), but that pack assists
   authoring only — it is never the gate and never a substitute for the
   deterministic engine, which remains the sole verification authority.

2. **Dataflow over pattern-matching.**
   The core engine is a taint/dataflow tracker (untrusted sources → dangerous
   sinks). Grep/regex-style rules are the exception, used only where dataflow
   genuinely does not apply, and must be marked as such.

3. **Every finding carries a confidence level: High / Medium / Low.**
   - High = deterministic, ~90%+ precision, safe to fail a build.
   - Medium = strong heuristic, advisory by default.
   - Low = informational, EXCLUDED from scoring.
   A rule may not ship as High without a measured precision number in
   `/benchmark`. If precision is unknown or <90%, it ships as Medium or Low.

4. **False positives are the enemy.** A noisy analyzer gets uninstalled. When in
   doubt between catching more and being wrong less, choose being wrong less.

5. **One rule = one detector module + one passing fixture + one failing fixture.**
   No rule is "done" until it has both a vulnerable fixture (must trigger) and a
   clean fixture (must NOT trigger), both in `/fixtures`, both under test.

6. **The Quality Gate is the product; the score is the dashboard.**
   Teams wire the pass/fail Quality Gate into CI. Scores (pillar scores +
   composite) are stakeholder roll-ups. Never make the score the CI mechanism.

7. **Reliability leads. Security is a competent pillar, not the headline.**
   When prioritizing what to build or which rules to deepen, the order is:
   Reliability → Architecture & Agentic Maturity → Harness Engineering →
   Security. We deliberately do NOT compete as "another security scanner."

8. **Standards-grade output.** SARIF output is mandatory and must validate
   against the SARIF 2.1.0 schema. Every rule maps to external standards where
   they exist (OWASP LLM Top 10, OWASP Agentic Top 10, NIST AI RMF, CWE).

9. **Capture every architectural decision as an ADR.** Any non-trivial
   design choice gets a numbered, immutable ADR in `/docs/adr` BEFORE or
   ALONGSIDE the code that implements it. ADRs are never edited after
   acceptance — only superseded by a new ADR.

10. **Naming hygiene.** The composite score is the **Readiness Score** (or
    "Reliability Score") — NEVER "Trust Score." "Trust Score" and "Trust
    Profile" belong exclusively to AgentGuard. Plumbline FEEDS those; it does
    not reproduce them.

---

## 2. Workflow Claude Code must follow

Work in tight, reviewable increments. The loop for every unit of work:

```
spec  →  ADR (if a decision is made)  →  test (failing)  →  implement  →
green tests  →  update docs  →  commit (with ADR reference)
```

- **Read before writing.** At session start, read this file, then the relevant
  spec in `/docs/specs`, then any ADRs touching the area. Never implement a
  component whose spec you have not read.
- **Small diffs.** Prefer many small, coherent commits over large ones. A diff a
  human cannot review in 10 minutes is too big. The failure mode of agentic
  coding is large unreviewed diffs that work but nobody understands — actively
  prevent it.
- **Test-first for rules and core.** Write the failing fixture/test, then the
  detector. A rule with no failing fixture is not allowed to exist.
- **No scope creep.** If you discover work beyond the current task, write it to
  `/docs/backlog.md` and keep going. Do not silently expand scope.
- **Surface conflicts, don't paper over them.** If a spec, an ADR, and the code
  disagree, stop and report the conflict. Do not pick one silently.
- **Determinism check.** After implementing any detector, mentally (or in test)
  confirm: same input → same output, no ordering dependence, no network, no
  clock, no randomness in the detection path.

---

## 3. Build sequence (the order of work)

Do NOT build rules first. Build the substrate, prove it end-to-end with ONE
rule, then scale. Phases:

1. **Substrate:** project skeleton, config loading, the Finding data model,
   the AST layer (Python `ast`/`libcst`), and ONE framework adapter
   (raw OpenAI/Anthropic SDK). No rules yet.
2. **Taint engine:** sources → sinks dataflow tracker. This unlocks most rules.
3. **First worked rule end-to-end:** `PLB-RES-001` (LLM call without timeout) —
   detector + fixtures + test + it appears in CLI and SARIF output. This proves
   the whole pipeline.
4. **Reporters + Quality Gate:** CLI (human-readable), SARIF 2.1.0, JSON.
   Quality Gate (default: zero Blockers AND zero High-confidence Criticals).
   Now it runs in CI.
5. **Reliability core:** the rest of the High-confidence RES, OUT, COST rules.
   This alone is a credible, demoable product and is the differentiated wedge.
6. **More adapters:** LangChain/LangGraph, then CrewAI; then the AGT/TOOL rules
   that depend on them.
7. **Harness pillar:** EVAL + OBS categories.
8. **Security pillar:** SEC + GOV. Shipped AFTER the differentiators — security
   is necessary but is not why anyone chooses Plumbline over existing scanners.
9. **Scoring:** pillar scores + Readiness Score + HTML report.
10. **AI-assisted remediation:** LLM generates fix text (detection stays
    deterministic).
11. **Phase 2 (separate milestone):** trace ingestion — the bridge to AgentGuard.

Rule IDs use the prefix `PLB-` (e.g., `PLB-RES-001`). The canonical rule list is
`/docs/specs/rule-catalog.md`.

---

## 4. Engineering standards

- **Language:** Python 3.11+. Type-hinted throughout; `mypy` clean.
- **Style:** `ruff` for lint+format. No hand-formatting debates.
- **Tests:** `pytest`. Every rule has fixtures under `/fixtures/<rule_id>/`.
  Target: every High-confidence rule has a precision measurement in
  `/benchmark`.
- **Dependencies:** minimal and justified. A new runtime dependency requires a
  one-line justification in the PR/commit message. The detection path has NO
  network dependency.
- **Public API stability:** the rule-plugin contract and the Finding schema are
  public contracts. Changing them requires an ADR.
- **Determinism in tests:** no rule test may depend on wall-clock, network, or
  randomness.
- **Errors fail loud in dev, soft in CLI.** A detector that crashes on a file
  must be caught at the engine boundary, reported as an analyzer error (not a
  finding), and must not abort the whole run.

---

## 5. The rule-plugin contract (summary — full spec in /docs/specs)

Every rule is a self-contained module exposing:
- a stable **ID** (`PLB-<CAT>-<NNN>`),
- metadata: title, category, pillar, severity, confidence, standards mappings,
  a one-line "why it matters,"
- a **detector** function: `(analysis_context) -> list[Finding]`,
- a remediation template (static text; AI may enrich at output time),
- fixtures: at least one failing (`bad_*.py`) and one passing (`good_*.py`).

Rules are discovered by convention from `/src/plumbline/rules/`. Adding a rule
must never require editing a central registry by hand (no merge-conflict
bottleneck for contributors).

---

## 6. What "best-in-class open source" means here (the bar)

- A first-time user gets value in under 5 minutes: `pip install actaclad-plumbline`,
  `plumb scan ./app`, useful output.
- A first-time contributor can add a rule in an afternoon by copying an existing
  rule's module + fixtures. The barrier is deliberately low.
- The README leads with the reliability/architecture positioning and the
  problem, not a feature list.
- Findings are actionable: every finding says what, where, why it matters, and
  how to fix it — with a standards reference.
- The tool is genuinely excellent standalone. It must NEVER feel like
  crippleware that exists only to upsell AgentGuard. The funnel is earned by
  being good, not by withholding.

---

## 7. The relationship to ActaClad and AgentGuard (keep this legible)

- Plumbline = **design-time**. AgentGuard = **runtime**. Same worldview.
- Plumbline's pillars (Reliability, Architecture & Agentic Maturity, Harness
  Engineering, Security) are the static precursors of AgentGuard's pillars
  (Observability, Evaluation, Security, Governance).
- Plumbline's Readiness Score is one input that can feed AgentGuard's
  nine-dimension Trust Profile. Do not duplicate or rename AgentGuard's
  artifacts inside Plumbline.
- License: Apache-2.0 (permissive, for adoption and contribution).

---

## 8. Tone and documentation voice

- Precise, engineer-to-engineer, no marketing fluff in code or docs.
- Every finding's "why it matters" is concrete (names the production failure),
  not abstract.
- When unsure, optimize for the reader who will maintain this in two years.
