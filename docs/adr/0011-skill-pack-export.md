# ADR-0011 — Skill-pack export: rules as a generation-time prevention artifact

- **Status:** Accepted
- **Date:** 2026-06-13
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

The same knowledge a Plumbline rule encodes ("a model/tool call without a
timeout can hang and exhaust the worker pool; here is the bad pattern and the
fix") is useful at *three* points in the software lifecycle, not one:

1. **Authoring** — an agentic coding tool (Claude Code, Cursor, Codex) that
   reads the rule as context will *generate* timeout-wrapped, fallback-having,
   bounded-loop code by default. This is prevention.
2. **Verification** — the deterministic engine *detects* the defect and gates
   CI. This is the product.
3. **Remediation** — an LLM tailors fix text at output time (ADR-0001 D2).

A tempting but fatal reading is "if an AI can apply the rules from markdown,
ship the rules as skills and drop the engine." This is rejected outright: it
violates ADR-0001 D2 (detection must be deterministic — an LLM gives
different findings run-to-run and cannot gate a build), it makes the
generator audit its own output (correlated, non-independent), it cannot
compute multi-hop taint reachability (the flagship detections), it is slow
and expensive per-PR, and it discards the defensible IP (engine + adapters +
taint + SARIF machinery) while keeping only the copyable part (the rule
prose). The engine is why this is a product and not a gist.

The opportunity is the *both/and*: ship a **skill-pack** for prevention
*and* keep the deterministic engine as the verification authority. The open
design question is how to avoid the two surfaces drifting apart.

## Decision

### D1 — The skill-pack is a generated export of the rule registry, not a new source

There is **no new "canonical knowledge" artifact** above the rule. The `Rule`
object plus its fixtures already are the single source of truth: the
rule-plugin contract (CLAUDE.md §5, `rule-plugin-contract.md`) already
mandates `id`, `title`, `pillar`, `severity`, `confidence`, `why_it_matters`,
`standards`, a `remediation` template containing bad/good examples, and a
mandatory bad/good fixture pair of realistic framework code.

A new command, `plumb export-skills`, walks the **same discovered rules**
(ADR-0005) and serializes that metadata — using the real fixtures as the
few-shot bad/good examples — into a skill/ruleset pack. Author once (the rule
module), render twice (detector + skill). Rejected: a separate
knowledge-definition file from which both detector metadata and the skill are
derived — the detector *logic* (taint queries, AST patterns,
`Absent`-vs-`Unknown` handling) cannot be derived from prose, so such a file
would not reduce drift, it would add a third thing to keep in sync.

### D2 — The export is mechanical and lives in the deterministic toolchain

The exporter performs string serialization of already-computed rule metadata.
**No LLM is involved in producing the pack** (the LLM only *consumes* it later
in a third-party coding tool). The export is therefore deterministic and
reproducible like every other Plumbline output, and is covered by the same
byte-equality discipline (ADR-0002 D3). It does no network I/O.

### D3 — Output format

`plumb export-skills --out <dir>` emits, deterministically (sorted by rule
ID):

- `SKILL.md` — an index/overview framing the pack ("write reliable agentic
  code by default") with the pillar grouping.
- `rules/<rule_id>.md` — one file per rule: title, pillar, *why it matters*,
  the bad example, the good example (from the fixtures), the fix guidance, and
  standards references.
- a `manifest.json` recording the package version and the rule IDs/count, so a
  consumer can detect staleness.

A `--format` flag selects render targets (v1: `claude-skill` directory layout;
`cursor-rules` and a single-file `agents-md` are additive later). The pack is
plain markdown — portable across tools by design.

### D4 — Positioning guardrail (a new invariant)

The skill-pack is a **distribution and prevention artifact, never the gate and
never a substitute for the engine.** Docs, README, and the pack's own
`SKILL.md` must state this. Prevention is allowed to be probabilistic
(mistakes are cheap — the verifier catches them); verification must be
deterministic (mistakes are expensive — a shipped defect or a phantom CI
break). An AI is fit for the first job; the engine is required for the second.
This sentence is added to the project guardrails.

### D5 — Scope and sequencing (the fence)

The exporter has nothing meaningful to emit until a credible rule set exists,
and it must **never** be built ahead of the engine. It is therefore an
**additive milestone after M3** (the reliability core), not part of the M0
substrate. It does not shift the meaning of M4–M9. It is a thin, reporter-like
feature (~one module + a CLI verb + golden tests), copying the determinism and
testing patterns the reporters already established.

## Consequences

- Plumbline's rule knowledge is deployed at all three lifecycle points from
  one authored source; a contributor who adds a rule improves prevention *and*
  verification in the same PR, with no extra artifact to maintain.
- The fixtures earn double duty: detection oracle *and* few-shot examples.
- The distribution surface (a drop-in skill pack for popular coding tools)
  widens reach to the moment of authorship and deepens the moat by making the
  rule catalog useful before CI — without weakening the deterministic engine
  that is the actual defensible product.
- A new invariant (D4) constrains positioning: the engine is the authority;
  the skill-pack assists. This is added to `CLAUDE.md` guardrails on approval.
- New backlog items: `cursor-rules` and `agents-md` render targets;
  auto-publishing the pack as a versioned release asset.
