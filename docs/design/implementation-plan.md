# Plumbline — Implementation Plan (M0–M9)

**Status:** Phase 1 plan, awaiting review. Companion: `detailed-design.md`.
Milestones follow `architecture.md` §9 / CLAUDE.md §3. Every milestone ends
green (`ruff`, `mypy --strict`, `pytest`) and shippable; each ends with a
review pause. Commits are small (≤ ~10-minute review), each referencing the
rule ID / ADR it implements.

Conventions for every milestone below: **Tasks** are individually
committable units in order; **DoD** is the definition of done.

---

## M0 — Substrate

Goal: the skeleton runs end-to-end with zero rules. `plumb scan .` prints
"0 findings (no rules loaded)".

Tasks (each one commit):
1. Repo hygiene: `git init` (if approved), accept ADRs 0002–0010, update
   `pyproject.toml` (drop `libcst`, drop `tomli`; ADR-0009/0007), CI workflow
   (ruff + mypy + pytest, 3.11–3.13).
2. `model.py`: enums, `Resolved`, `SemanticNode`, `Finding`, `AnalyzerError`
   + fingerprint function with property tests (ADR-0002).
3. `config.py`: schema, strict validation, precedence, gate evaluation
   stub + tests; regenerate-example test (ADR-0007).
4. `core/ast_layer.py`: parse wrapper, parent/scope tables, segments,
   suppression-comment scan + tests (ADR-0009).
5. `core/values.py`: literal folding + client linking + tests (ADR-0004 D3).
6. `adapters/base.py` + `adapters/openai_sdk.py` + golden tests
   (adapter-contract §5/§6).
7. `rules/base.py`: `Rule`, `Scope`, contexts, discovery + validation +
   meta-test (ADR-0005, ADR-0010) — discovering an empty tree.
8. `engine.py` walking skeleton + `cli.py` `plumb scan` / `plumb rules`,
   exit codes; end-to-end test on a toy directory.

DoD: fresh `pip install -e ".[dev]"` → `plumb scan .` works; all contracts
type-checked under `mypy --strict`; double-run byte-equality test exists and
passes (trivially, zero findings); no rule code anywhere.

## M1 — Taint engine + PLB-RES-001 end-to-end

Tasks:
1. `core/taint.py` propagation core, test-first per taint-engine §8
   (several commits: environment/fixpoint → propagation rows → summaries →
   witness paths).
2. Wire taint into the engine + `AnalysisContext`.
3. PLB-RES-001: failing fixtures first (`bad_no_timeout.py`,
   `bad_client_unbounded.py`, `good_client_timeout.py`,
   `good_call_timeout.py`), then detector honoring `Absent`-vs-`Unknown`
   (detailed-design §9.4), then the rule test via the shared harness.
4. Minimal SARIF reporter (schema-valid; vendored schema) + CLI reporter
   showing the finding richly.

DoD: `plumb scan fixtures/PLB-RES-001/bad_no_timeout.py` shows the finding in
CLI and valid SARIF; good fixtures silent; the full pipeline (parse → adapt →
taint → rule → report) covered by the double-run test. **This proves the
architecture; pause for review here even mid-milestone-cadence.**

## M2 — Reporters + Quality Gate

Tasks: JSON reporter (serialized `ScanResult`); SARIF completion (rule
metadata for all rules, codeFlows, notifications, suppressions); baseline
file + `plumb baseline` (ADR-0006 D5); inline suppressions (D6); Quality Gate
wiring + exit codes + `--strict-analyzer-errors`; docs: CI integration guide
(GitHub Actions snippet).

DoD: a CI pipeline can install, scan, gate, and upload SARIF to GitHub code
scanning; baseline adoption flow works on a seeded repo fixture; exit-code
contract covered by subprocess tests.

## M3 — Reliability core (the wedge)

Rules, in order (test-first, one rule = one commit series; severities/
confidences per catalog, with M3 shipping initially at **Medium** where the
benchmark hasn't yet measured precision — promotion to High happens inside
this milestone once measured):
PLB-RES-002, RES-003, RES-005, RES-006 (file-scope); RES-008 (file-scope);
OUT-001, OUT-003 (file-scope); COST-001 (file-scope); MDL-002 (needs the
deprecated-model data file — packaged data, versioned with releases);
RES-004 + MDL-001 (project-scope — exercise ADR-0010, incl. directory
fixtures).

Benchmark harness lands here: labeled corpus (≥ 10 real OSS agentic repos,
pinned commits, vendored snapshots or submodules — decision recorded in the
corpus README), per-rule precision report committed to `/benchmark`;
standards-map precision column filled for every High promotion.

DoD: the demoable wedge — a real agentic repo scan produces meaningful
reliability findings; every High-confidence rule has a measured precision
≥ 90% in `/benchmark`; catalog + standards map updated.

## M3+ — Skill-pack export (additive; after M3, never ahead of the engine)

Goal: ship the rule knowledge as a generation-time prevention artifact
(ADR-0011). Additive — does not shift M4–M9. Buildable any time once a
credible rule set exists (≥ the reliability core).

Tasks:
1. `skills/export.py`: walk the discovered rule registry (ADR-0005),
   serialize each rule's metadata + remediation + its real bad/good fixtures
   into markdown; deterministic, sorted by rule ID, no LLM, no network.
2. `plumb export-skills --out <dir> [--format claude-skill]`: emit `SKILL.md`,
   `rules/<rule_id>.md`, `manifest.json` (ADR-0011 D3).
3. Golden tests on the emitted pack; byte-equality (double-run) like the
   reporters; a test asserting every discovered rule appears in the pack.
4. Docs: README section framing the pack as **prevention, not the gate**
   (ADR-0011 D4); a "use Plumbline rules in your coding tool" guide.

DoD: `plumb export-skills` produces a portable markdown pack from the live
rule set; golden + determinism tests green; positioning guardrail (D4)
present in docs; `cursor-rules`/`agents-md` formats recorded in backlog.

## M4 — LangChain/LangGraph + CrewAI adapters, AGT/TOOL rules

Tasks: `adapters/langchain.py` (pattern table spec PR first, per
adapter-contract §7) → rerun whole rule suite over its fixtures (precision
regression check) → `adapters/crewai.py` same flow → rules AGT-001, AGT-002,
AGT-004 (High set), AGT-003, AGT-005, AGT-006 (Medium), TOOL-001…004
(TOOL-002/004 are the first real taint-rule consumers beyond RES; witness
paths must read well in messages).

DoD: one rule, three frameworks: AGT-001 fires on LangChain, CrewAI, and
hand-rolled loops via the same detector; adapter golden tests green;
benchmark rerun, no precision regressions.

## M5 — Harness pillar (EVAL + OBS)

Rules: EVAL-001 (project-scope; ships **Medium** until the benchmark proves
otherwise — see open question in the Phase 1 review), EVAL-002, EVAL-003
(reframed statically: CI config files scanned for eval invocation — its
detector spec must be written and approved as part of this milestone),
OBS-001 (project-scope), OBS-002.

DoD: harness-pillar findings render with the "you are flying blind" story;
fixtures include realistic pytest/eval-suite layouts; precision measured for
any High candidate.

## M6 — Security pillar (SEC + GOV)

Rules: SEC-001…007 (taint showcase; SEC-004 is the one sanctioned
pattern-rule, marked as such per CLAUDE.md §1.2), GOV-001, GOV-002.
Benchmark these against the existing security scanners' public test sets
where licensing allows — we should not be worse than the incumbents on the
commodity pillar.

DoD: full launch-40 present minus deferred Low-confidence rules; OWASP/CWE
mappings complete in standards-map; precision measured for all High rules.

## M7 — Scoring + HTML report

Tasks: `scoring/pillars.py` + `scoring/readiness.py` implementing ADR-0008
exactly (the D4 vector is the first test); N/A semantics; HTML reporter
(self-contained single file, no CDN — works offline; scores + pillar
breakdown + findings table); CLI score summary block.

DoD: ADR-0008 worked example reproduced bit-exactly; HTML renders without
network; "Readiness Score" naming verified everywhere (grep gate in CI for
"Trust Score").

## M8 — AI-assisted remediation (optional layer)

Tasks: `[ai]` extra wiring; enrichment runs **after** `ScanResult` is final,
only rewrites remediation *text*, clearly labeled in output; offline/no-key
behavior identical to disabled; a test asserting findings/fingerprints/gate
are byte-identical with enrichment on/off (the determinism firewall).

DoD: enrichment demonstrably cannot alter detection; docs explain the
boundary; feature is off by default.

## M9 — Phase 2: trace ingestion (separate milestone, separate design)

Not designed here. Entry criterion: a Phase-2 design doc + ADRs (trace
format, AgentGuard interface). Deliberately out of v1 scope.

---

## Cross-milestone rules of engagement

- The loop per unit of work: spec → ADR (if deciding) → failing test →
  implement → green → docs → commit (CLAUDE.md §2).
- Discovered out-of-scope work goes to `docs/backlog.md`, never inline.
- A milestone ends with: full CI green, docs current (catalog, standards
  map, README where relevant), a short milestone summary for review, and a
  **stop for maintainer review** before the next begins.
- Rule promotion to High confidence happens only via a `/benchmark` precision
  commit, never by editing the rule alone.
