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

## Discovered during M0

- **Full `.gitignore` semantics.** `[scan].respect_gitignore` defaults true but
  M0 only honors the built-in `default_excludes` set + `[scan].exclude` globs;
  real nested/negated gitignore parsing is deferred. The config flag is accepted
  but not yet fully effective — surfaced here per CLAUDE.md §2.
- **PROMPT_BUILD / AGENT_LOOP tags** are defined in the vocabulary but the
  openai_sdk adapter does not yet emit them; add when their consuming rules
  (PRM, AGT) are built (M4).

## Skill-pack export (ADR-0011) follow-ons

- Additional render targets beyond `claude-skill`: `cursor-rules` and a
  single-file `agents-md`.
- Auto-publish the skill-pack as a versioned release asset in CI.

## Nice-to-have (unscheduled)

- Pre-commit hook distribution.
- GitHub Action wrapper for one-line CI adoption.
- A `plumb explain PLB-RES-001` command that prints the rule's rationale +
  examples (docs-as-CLI).
- VS Code / editor integration consuming the SARIF output.
- A rendered, published OWASP/NIST coverage matrix on the docs site.
