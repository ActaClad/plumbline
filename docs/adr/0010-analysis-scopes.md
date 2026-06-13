# ADR-0010 — Analysis scopes: file-scope and project-scope rules

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

The rule-plugin contract defines `detect(ctx) -> list[Finding]` over a
per-file `AnalysisContext`. But several launch rules are not answerable from
one file: PLB-EVAL-001 ("no eval suite in the repo"), PLB-OBS-001 ("no
tracing configured anywhere"), PLB-MDL-001 ("model literals scattered across
modules"), PLB-RES-004 ("exactly one provider on the request path"),
PLB-RAG-004 ("index-time vs query-time embedding model differ"). Detailed
design must say how these run without breaking the per-file contract or
determinism.

## Decision

### D1 — Two declared scopes, one Rule contract

`Rule` gains a `scope` field: `Scope.FILE` (default) or `Scope.PROJECT`.

- **FILE** rules keep the existing signature:
  `detect(ctx: AnalysisContext) -> list[Finding]`, called once per analyzed
  file, in sorted file order.
- **PROJECT** rules implement
  `detect(ctx: ProjectContext) -> list[Finding]`, called exactly once per
  run, **after** all file analyses complete.

`ProjectContext` provides read-only access to: the scan root and sorted file
list; every file's `AnalysisContext` (AST, semantic nodes, taint results);
aggregate indexes the engine builds anyway (all semantic nodes by tag, all
model-name literals with locations); and the effective config. Project rules
are subject to the same purity rules as file rules — they may not do I/O; the
engine has already read everything.

Rejected: making every rule project-scope (forces 90% of rules to loop over
files themselves and bloats memory pressure into the contract); a separate
"repo checks" subsystem outside the rule contract (two contracts to learn,
two discovery mechanisms, two fixture conventions — for five rules).

### D2 — Project-scope findings still anchor to a real location

SARIF and the CLI need a file/line. A project rule must anchor each finding
to the most relevant deterministic location (e.g. PLB-EVAL-001 anchors to the
first `LLM_CALL` in sorted file order — "this is the code you are shipping
blind"). Anchoring rules are part of each rule's spec entry; "first X in
sorted order" is the default idiom. No finding may anchor to a synthetic
path.

### D3 — Fixtures for project-scope rules are directories

`fixtures/<RULE_ID>/bad_*/` and `good_*/` are **directories** (mini-repos)
for project-scope rules, instead of single files. The fixture test harness
detects which form a rule uses by what exists on disk. The
one-bad-one-good-minimum principle is unchanged.

### D4 — Memory boundary

Holding every file's full `AnalysisContext` is acceptable for v1 target repo
sizes (the AST is the dominant cost; a 100-kLOC repo is on the order of
hundreds of MB worst-case, typically far less because non-AI files get no
taint/semantic analysis). If profiling on real repos breaks this, the fix is
to slim what `ProjectContext` retains per file (semantic nodes + indexes,
dropping ASTs) — that change would need a superseding ADR only if it changes
the rule-facing API.

## Consequences

- All five repo-level launch rules fit the standard contract, discovery, and
  fixture conventions; contributors learn one model with one flag.
- Engine ordering becomes: analyze all files (sorted) → run project rules
  (sorted by rule ID) → merge, dedupe, sort findings (ADR-0002 D3) — still
  fully deterministic.
- The fixture harness gains directory-fixture support in M1 (cheap to build
  alongside file fixtures).
