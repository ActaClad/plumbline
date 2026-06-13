# ADR-0009 — AST layer: stdlib `ast` for detection; libcst deferred to autofix

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

ADR-0001 and `architecture.md` say "Python `ast`/`libcst`" without choosing;
the current `pyproject.toml` already lists `libcst>=1.1` as a runtime
dependency "for the AST layer." Detailed design forces the choice: the AST
layer is the substrate everything reads, and the two libraries differ sharply
in speed and in what they preserve.

## Decision

v1 detection parses with **stdlib `ast`**. `core/ast_layer.py` wraps it with
what detection actually needs: a parent map, a scope table (module /
function / class scopes with symbol bindings), per-node source-segment
extraction (`ast.get_source_segment` over the kept source text), and end
positions (native since 3.8). Comments — needed only for inline suppressions
— are read separately via stdlib `tokenize` (ADR-0006 D6).

**`libcst` is removed from runtime dependencies** until the feature that
genuinely needs lossless CST — automated fix application — is scheduled
(M8+ at the earliest; its addition will be a superseding ADR).

Why `ast` wins for detection:

1. **Speed.** Parsing with `libcst` is roughly an order of magnitude slower
   than `ast`. Plumbline's habitat is CI and pre-commit on whole repos;
   parse time is the dominant cost for a clean repo, and "value in under
   5 minutes" (CLAUDE.md §6) includes scan latency.
2. **Sufficiency.** Detection needs structure, positions, and source
   snippets — all of which `ast` provides. Formatting/comment fidelity, the
   thing libcst exists for, is needed only for *rewriting* code, which v1
   explicitly does not do (remediation is text, ADR-0001 D2).
3. **Zero-dependency substrate.** The detection path's only parse dependency
   becomes the interpreter itself — fewer supply-chain and version-matrix
   concerns for a tool teams gate CI on.

Risks accepted: (a) stdlib `ast` tracks the Python grammar of the running
interpreter, so scanning code using newer syntax than the host Python fails
to parse — reported as an `AnalyzerError` for that file, never a crash;
(b) if autofix lands later, libcst returns and the AST layer grows a second
backend — the wrapper API is designed so rules never import `ast` types
through it for anything libcst cannot also anchor (rules receive node
references and helpers, and treat them as opaque anchors where possible).

## Consequences

- `pyproject.toml` drops `libcst` (and the dead `tomli` conditional — see
  ADR-0007 D1); the detection path's runtime deps become `click` + `rich`
  only.
- Whole-repo scans stay fast enough for pre-commit use.
- The AST wrapper, not raw `ast`, is the rule-facing surface; this is what
  makes a future second backend possible without breaking the rule contract.
