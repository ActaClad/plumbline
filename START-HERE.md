# START HERE

You are about to build **Plumbline** — an open-source reliability and
architecture analyzer for LLM and agentic systems, built by ActaClad, using
agentic coding (Claude Code). This file orients the first session. Read it once,
then follow the reading order.

## What this repo is

A static analyzer that answers *"will this agentic system fall over in
production?"* It is **not** a style linter and **not** (primarily) a security
scanner — it leads on reliability and architecture. The full rationale is in the
constitution and ADR-0001. Do not re-litigate the positioning; it was decided
deliberately.

## Reading order (do this before writing any code)

1. **`CLAUDE.md`** — the project constitution. Non-negotiable principles, the
   workflow loop, the build sequence, engineering standards. This governs every
   session. If anything ever conflicts with it, it wins.
2. **`docs/adr/0001-foundational-decisions.md`** — *why* the project is the way
   it is (positioning, determinism, taint-first, confidence model, scoring,
   plugin architecture, build order). ADRs are immutable; new decisions get new
   ADRs.
3. **`docs/specs/architecture.md`** — the module layout, the Finding data model,
   the pipeline, and the milestones (M0–M9). This is what you implement the
   skeleton from.
4. **`docs/specs/rule-plugin-contract.md`** — how every rule is written and
   discovered, with the worked `PLB-RES-001` example. This is the template the
   whole rule set scales from.
5. **`docs/specs/rule-catalog.md`** — the canonical rule list (reliability-led),
   ~54 rules with severity/confidence/mappings. The launch set and cut-line are
   marked.
6. Skim `CONTRIBUTING.md`, `docs/rule-authoring.md`, `docs/standards-map.md`,
   `docs/backlog.md`, `docs/content-plan.md` as needed.

## What to build first (M0 → M1)

Per `CLAUDE.md` §3 and `architecture.md` §9 — **do not start with rules.**

- **M0 Substrate:** finish `pyproject.toml` wiring, implement `model.py` (the
  Finding model), `config.py`, `core/ast_layer.py`, and the `openai_sdk`
  adapter. The CLI should run and report "no rules loaded." Keep diffs small;
  commit per component.
- **M1 Taint + first rule:** implement `core/taint.py` (sources→sinks), then
  build **`PLB-RES-001`** end-to-end — detector + `fixtures/PLB-RES-001/`
  (bad + good) + test — and make it appear in CLI and SARIF output. This proves
  the entire pipeline. Everything else scales from this one rule.

Write an ADR whenever you make a non-trivial design decision (e.g., the exact
taint representation, the SARIF baseline format, the scoring formula). Use
`docs/adr/TEMPLATE.md`.

## The discipline that makes this work

- Spec → ADR (if deciding) → failing test → implement → green → docs → commit.
- Detection is deterministic. No network/clock/randomness in the detection path.
- One rule = one detector + one bad fixture + one good fixture + a test.
- No rule ships as High confidence without a measured precision in `/benchmark`.
- When you find out-of-scope work, write it to `docs/backlog.md` and keep going.
- Small, reviewable commits. Never a diff a human can't review in 10 minutes.

## The bar

Best-in-class open source: value in under 5 minutes for a user, a new rule in an
afternoon for a contributor, every finding actionable with a fix, genuinely
excellent standalone (never crippleware for AgentGuard). Build to that bar.

Begin with M0. Read `CLAUDE.md` now.
