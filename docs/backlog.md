# Backlog — discovered-but-deferred work

When work is found mid-task that is out of current scope, record it here and keep
going (CLAUDE.md §2). Triage periodically. This is not the roadmap (that's the
milestones in `specs/architecture.md`) — it's the catch-net.

## Deferred to later milestones (intentional, from planning)

- **Cross-module / inter-procedural taint.** v1 taint is intra-procedural with
  simple local-call propagation (ADR-0001 D3 / taint spec). Full inter-module
  flow is a later milestone — write an ADR when starting it; several Medium
  rules can graduate toward High once it lands.
- **Low-confidence launch rules deferred to v1.1:** PLB-RES-009, PLB-AGT-007,
  PLB-MDL-005, PLB-RAG-003, PLB-EVAL-004, PLB-OBS-003, and the thinnest
  RAG/PRM/GOV rules — unless a design partner pulls one forward.
- **MCP & A2A protocol rules** (the `MCP` category from the broader taxonomy) —
  not in the launch-40; high-interest, add once core is stable.
- **JavaScript/TypeScript support.** v1 is Python only. Multi-language is a
  major effort gated behind a stable Python core and the adapter contract
  proving itself. Resist early.
- **AI-assisted remediation enrichment** (M8) — detection stays deterministic;
  this only tailors fix text at output time.
- **Trace ingestion / AgentGuard bridge** (M9 / Phase 2) — turns static "risk"
  flags into runtime-confirmed "incident" findings.

## Known doc divergences (cosmetic, immutable ADRs)

- **ADR-0012 D3 worked example.** The row `while n < MAX: … n += 1 →
  has_iteration_cap=Known(True)` describes the *intent*; the implementation
  returns `UNKNOWN` for any non-constant `while` test (counter detection runs
  only on truthy-constant `while True`). Both yield the same outcome — AGT-001
  stays silent (conservative, no false positive) — so the divergence is
  cosmetic. The ADR is immutable; this note records it. If a future change wants
  `Known(True)` there (e.g. for scoring), supersede ADR-0012.

## Open questions to resolve via ADR before building

- ~~Exact pillar-score formula and Readiness Score weighting~~ — resolved by
  ADR-0008 (worked example included).
- ~~Baseline/suppression file format for SARIF~~ — resolved by ADR-0006.
- ~~Config file schema (`.plumbline.toml`)~~ — resolved by ADR-0007.
- Third-party rule packages via an entry-point group (`plumbline.rules`) —
  deferred from ADR-0005 D4; design so it's additive.
- Score density-normalization (per-KLOC) once real-repo telemetry exists —
  would supersede ADR-0008.
- Engine parallelism (per-file workers) — only behind the double-run
  byte-equality determinism test (detailed-design §3).

## Rule ideas

- **"Relies on SDK-default timeout" — Medium advisory (RES).** Distinct from
  PLB-RES-001 (which fires only on explicit `timeout=None`): flag LLM calls that
  rely on the SDK's finite-but-long default timeout (OpenAI/Anthropic ~600s),
  which can still exhaust a worker pool under load. Medium/advisory so it does
  not gate idiomatic code; complements RES-001's High/Blocker explicit-disable
  case. (Requested 2026-06-13.)

## Deferred from M3 (reliability core) — need substrate or are heuristic

- **PLB-RES-003 (retry without backoff)** and **PLB-RES-006 (no 429 handling)**:
  need detection of retry constructs (tenacity, `@retry`, hand-rolled loops).
  With only the raw-SDK adapter there is no retry construct to inspect (the SDK
  retries internally with backoff). Add alongside retry-construct semantics.
- **PLB-RES-008 (unbounded memory growth)**: heuristic (list `.append` in a
  loop/handler with no trim); Medium. Build once there's a `MEMORY_APPEND`
  signal or a careful loop-pattern detector — risks noise otherwise.
- **PLB-OUT-003 (no empty/refused/truncated handling)**: needs finish-reason /
  empty-content flow detection; "no check" is hard to do precisely. Heuristic.
- **PLB-RES-004 (no fallback / single provider)**: project-scope, but detecting
  a *fallback path* statically is genuinely heuristic and noisy. Defer until a
  precise fallback-pattern signal exists; MDL-001 is the M3 project-scope
  showcase instead.
- **PLB-MDL-002 (deprecated model id)**: feasible (string match against a
  maintained deprecated-model list) but needs a packaged, versioned data file.
  Add with the data file + its refresh process.

## Deferred from M8 (AI remediation) — additive polish

Shipped: the enrichment firewall, AnthropicEnricher, off-by-default config, CLI
wiring (ADR-0015). Additive follow-ons:

- **Configurable model / provider.** `AIConfig` only carries `enrich_remediation`;
  the model is hard-coded and the provider is Anthropic-only. Add `[ai] model`
  and an OpenAI enricher behind the same `Enricher` protocol when wanted (changes
  the config schema → touches ADR-0007's example-TOML lock).
- **Batch / cached enrichment.** One API call per finding is simple but chatty;
  batch by rule, or cache by fingerprint so re-scans don't re-enrich unchanged
  findings.
- **`max_tokens=400` can truncate a long remediation mid-sentence.** Harmless
  (the text is advisory, never gating, and the static fallback is always present
  on error), but disclosed: raise the cap or stream if longer fixes are wanted.
- **HTML/SARIF AI labelling.** The CLI and JSON mark `(AI-assisted)`; the HTML
  report and SARIF could surface it too (SARIF deliberately keeps the static rule
  remediation as the machine contract).

## Known detection edges (disclosed from the hardening pass)

- **External real-repo validation is still undone.** Every measured "100%
  precision" is on a corpus + a realistic app *authored by the same agent that
  wrote the rules*, so it can only surface false positives we already thought to
  construct. The original aspiration — point Plumbline at ≥10 real OSS agentic
  repos and triage — remains the real precision/recall test. v0.1 ships without
  it; do not read "hardened" as "validated in the wild".
- **OpenAI Assistants API generations are not detected (recall gap).**
  `client.beta.threads.runs.create(...)` is the actual Assistants generation; its
  tail is `runs.create`, not in the call-tail set, so it is untagged. (The
  related `threads.messages.create` FALSE positive — it only adds a message — is
  now excluded.) Add Assistants-API run tags when that surface matters.
- **Test harness `run_project_rule` does not compute `project_roots`**, so it
  diverges from `scan()` on ADR-0016 project-triggering. Benign today (every
  project-rule fixture imports the SDK in-file) and the real engine path is
  covered by `test_cross_module`; tighten the harness if a cross-module
  project-rule fixture is ever added.

## Cross-module detection residuals (ADR-0016) — named, not fixed

Project-level triggering (ADR-0016) fixed cross-module detection for the raw
OpenAI SDK (the dominant pattern). Two residuals remain, disclosed:

- **Framework cross-module linking.** `from .llm import model; model.invoke()`
  still can't link `model` to its `ChatOpenAI()` construction in another file, so
  LangChain/CrewAI calls through a centralized handle stay untagged. Needs
  cross-module symbol resolution — a larger change than project-triggering.
- **Anthropic cross-module `messages.create`.** Because `.messages.create` is
  ambiguous with Twilio's SMS API, it is tagged only when openai/anthropic is
  imported in the same file. A centralized *Anthropic* client used cross-module
  is therefore missed (OpenAI, the common case, is caught). Closing this needs a
  receiver-typing signal to tell an Anthropic client from a Twilio one.

## Deferred from M6 (security pillar) — needs a sharper signal

Shipped: SEC-002/003/004/005/006 (High), SEC-007 + GOV-001/002 (Medium); SARIF
codeFlows (ADR-0014). Deferred:

- **PLB-SEC-001 (untrusted input reaches a tool-enabled prompt)** — as stated
  this describes *most* user-facing agents (putting user input in the prompt is
  the point; `tools=` set is normal), so it flags the architecture, not a defect.
  The real defect needs a *mediation* signal we don't have statically: untrusted
  content reaching a tool-capable model with **no delimiting/role-separation**
  between source and tool. Same call as TOOL-002/004 — defer until that signal
  exists. (Highest-FP rule in the set; must not ship as a gating Blocker.)
- **SEC taint recall is intra-procedural by design (ADR-0003).** The SEC rules
  miss cross-function source→sink flows; the benchmark recall column will read
  low and that is correct (precision over recall, CLAUDE.md §1.4). Do NOT loosen
  taint to chase it. Cross-procedural flow is its own backlogged milestone.
- **Benchmark against incumbent scanners' public test sets** (the M6 DoD's
  aspirational line) — licensing-gated. We ship our own safe-form FP-stress
  corpus; comparing against third-party suites (e.g. the security
  scanners' fixtures) where licensing allows is a follow-on.
- **SEC-005 `.execute` receiver is not type-resolved.** SEC-005 (Blocker/High)
  fires on `<x>.execute(tainted_query)`; the receiver `<x>` isn't typed, so a
  tainted arg0 to a *non-DB* `.execute()` (some driver/ORM method taking a
  command string) would be a false positive. Frequency is low in practice
  (redis `.execute()` takes no args; SQLAlchemy `.execute(text(...))` is SQL;
  `concurrent.futures` uses `submit`), so not narrowed in v1 — but it is a
  gating Blocker, so the residual is disclosed here, not assumed away. Fix needs
  receiver typing / a DB-cursor signal.
- **Richer secret detection (SEC-004)** — entropy scoring and more provider
  patterns (Stripe, Twilio, JWT, PEM blocks) would raise recall; the v1 set is
  the common high-signal shapes. Additive.

## Deferred from M5 (harness pillar) — approval gate or heuristic

Shipped: EVAL-001, OBS-001, **EVAL-003** (all Major/Medium, project-scope; see
`docs/specs/harness-rules.md`). EVAL-003 was approved at the M5 review (ADR-0013
Accepted) and is now built on the non-Python CI-evidence channel. Deferred:

- **PLB-EVAL-002 (no golden dataset / ground-truth fixtures)** — distinguishing
  "asserts against reference outputs" from "asserts it ran" is genuinely noisy
  statically (assertions take countless shapes; golden data may be inline, in
  fixtures, or external). High false-positive surface; defer until a precise
  signal exists.
- **PLB-OBS-002 (no run/session/user IDs on calls)** — correlation IDs are
  usually injected via middleware/context/callbacks, not call kwargs, so this
  shares OBS-001's env/middleware blind spot with less payoff. Defer.

## Deferred from M4 (adapters + AGT/TOOL) — substrate or heuristic

The M4 task list named AGT-001/002/003/004/005/006 and TOOL-001…004; the M4
**DoD** gates only on AGT-001 firing across three frameworks + adapter goldens +
no precision regression. Shipped: AGT-001, AGT-002, TOOL-001 (all High, measured
100%). Deferred, with reasons (surfaced per CLAUDE.md §2):

- **PLB-TOOL-002 (tool args used without validation)** and **PLB-TOOL-004 (tool
  output to prompt without sanitization)**: these are taint rules needing
  substrate that does not exist yet — a tool-argument taint *source* (seed
  `TOOL_DEF` params like web-handler params), a `PROMPT_BUILD` sink emission, and
  a validation/sanitizer sink catalog. That catalog overlaps the M6 SEC sinks;
  building it is an ADR-worthy decision. Defer to a taint-substrate milestone
  (with M6) rather than ship heuristic taint rules at low precision.
- **PLB-AGT-004 (no global run timeout / token budget)**: for framework agents,
  `max_iterations` already bounds the run in steps, so a separate wall-clock /
  token-budget rule risks firing on every bare executor (noise). Needs design:
  when is a wall-clock budget genuinely required vs. redundant with the step
  cap? Defer until that line is drawn.
- **PLB-TOOL-003 (tool has no error handling / can crash the agent run)**: a
  control-flow rule like RES-005 (a tool body making external calls with no
  try/except returning a structured error). Needs no new substrate — buildable
  next. Deferred only to keep the M4 diff reviewable; pull forward early in M5.
- **PLB-AGT-003 (unbounded recursion in planner / sub-agent spawning)**: needs a
  self-/sub-agent-invocation signal and a depth-parameter check; inherently
  heuristic. Medium when built.
- **PLB-AGT-005 (no verification/critique node)** and **PLB-AGT-006 (no HITL gate
  before irreversible action)**: graph-shape heuristics over AGENT graphs — high
  false-positive surface without a richer graph model. Medium; build with a
  dedicated graph-structure pass.
- **Aliased tool-decorator detection.** The langchain/crewai adapters match the
  `@tool` decorator by its local name; `from crewai.tools import tool as t` then
  `@t` is missed. resolve_qualified-based decorator resolution would make it
  alias-proof (as it already is for constructors). Low priority (rare).
- **Blocking-worker `while True` loops are a residual AGT-001/002 false-positive
  class.** The derivation pass excludes interactive REPLs (loop body contains
  `input()`, ADR-0012 D2) so a human-gated `while True` no longer fires. But a
  *blocking-queue/socket worker* — `while True: msg = q.get(); llm.create(msg)`
  with no break — is still tagged AGENT_LOOP and fires AGT-001 (no cap) and
  AGT-002 (no goal exit), even though it is a legitimate daemon bounded by the
  external queue, not the model. A `.get()`/`.recv()` name match is too broad to
  exclude safely (`dict.get`). The precise discriminator is *model-output
  feedback*: a true runaway agent loop re-feeds the model's output into the next
  iteration's prompt; a worker does not. Implementing that needs the taint
  engine to track list-append mutation (it currently does not — `.append` is not
  a return-propagator), or a dedicated loop-carried-feedback pass. Until then,
  this class is disclosed, not silently dropped (CLAUDE.md §1.4).
- **Mixed-/inline-client `.invoke()` linking.** LangChain `LLM_CALL` is tagged
  only when the receiver links to a model construction by single assignment;
  LCEL pipes (`chain = prompt | model`) and inline `ChatOpenAI().invoke()` are
  under-tagged (precision over recall). Revisit with richer expression tracking.

## Discovered during M1

- **SARIF `codeFlows` for taint findings.** ADR-0006 D3 wants taint witness
  paths emitted as `codeFlows`. The witness lives in `TaintView`, not on the
  `Finding` (whose fields are fixed by ADR-0002), so emitting it needs a
  `Finding` schema addition (an optional code-flow), which is an ADR. Defer
  until the first taint-based rule that wants it (M6 SEC rules); no current
  finding carries a witness, so there is nothing to emit yet.

## Discovered during M0

- **Full `.gitignore` semantics.** `[scan].respect_gitignore` defaults true but
  M0 only honors the built-in `default_excludes` set + `[scan].exclude` globs;
  real nested/negated gitignore parsing is deferred. The config flag is accepted
  but not yet fully effective — surfaced here per CLAUDE.md §2.
- **PROMPT_BUILD tag** is defined in the vocabulary but no adapter emits it yet;
  add when its consuming rules (PRM, and the deferred TOOL-004 taint sink) are
  built. (AGENT_LOOP — also listed here originally — now ships via the M4
  derived-semantics pass, ADR-0012.)

## Skill-pack export (ADR-0011) follow-ons

Shipped: `plumb export-skills` (claude-skill format) — SKILL.md + per-rule pages
+ manifest.json, deterministic, from the live rule registry. Follow-ons:

- Additional render targets beyond `claude-skill`: `cursor-rules` and a
  single-file `agents-md` (the `--format` flag is already in place).
- Auto-publish the skill-pack as a versioned release asset in CI.
- **Validate the `claude-skill` pack against a live skill loader.** SKILL.md now
  carries `name`/`description` frontmatter, but the format hasn't been loaded by
  an actual Claude/Agent skill runtime end-to-end — confirm the frontmatter
  fields and directory layout a real loader expects, or rename the format to
  `markdown` if it's a portable doc rather than a drop-in skill.
- **Fixtures must be on disk for the bad/good examples.** The exporter reads
  `fixtures/<rule_id>/` at export time, so a bare `pip install` (which doesn't
  ship test fixtures) produces rule pages *without* the embedded examples (the
  metadata + remediation still render). Either package fixtures as data, or have
  `export-skills` fall back to the remediation's inline Bad/Good snippets. The
  intended use today is exporting from a source checkout.

## Nice-to-have (unscheduled)

- Pre-commit hook distribution.
- GitHub Action wrapper for one-line CI adoption.
- A `plumb explain PLB-RES-001` command that prints the rule's rationale +
  examples (docs-as-CLI).
- VS Code / editor integration consuming the SARIF output.
- A rendered, published OWASP/NIST coverage matrix on the docs site.
