# ADR-0003 — Taint engine representation and the v1 scope boundary

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

ADR-0001 D3 makes the taint engine the substrate, built before rules.
`architecture.md` §4 fixes the v1 scope as "intra-procedural with simple
inter-procedural propagation through direct local calls" but leaves the
representation, the propagation semantics, the unknown-call policy, and the
query API undecided. These choices determine the precision/recall balance of
every dataflow rule, so they must be explicit. Full spec: `specs/taint-engine.md`.

## Decision

### D1 — Representation: label propagation over the AST, per function scope

The engine computes, for every expression node, a `frozenset[TaintLabel]`
(labels: `USER_INPUT, LLM_OUTPUT, TOOL_RESULT, RETRIEVED_CONTENT,
EXTERNAL_HTTP, PII`). It is:

- **forward and flow-sensitive** in statement order within a scope,
- **path-insensitive**: branches union their effects (no branch pruning),
- computed by a **worklist fixpoint over the statement list** per scope
  (loops converge because the lattice — label sets under union — is finite
  and propagation is monotone),
- run over **module scope and each function scope**; module-level variable
  taint flows into functions that read those names.

There is no CFG/SSA construction in v1. Rejected: a full CFG+SSA dataflow
framework (correct long-term, but weeks of substrate work that no launch rule
needs — the launch flows are straight-line or simple-loop) and a purely
syntactic single-pass (misses loop-carried flows like
`history.append(llm_out)` feeding the next iteration's prompt).

### D2 — Sources come from the adapter layer plus a small built-in registry

LLM/agent-specific sources are derived from semantic tags (ADR-0004): the
result of an `LLM_CALL` is `LLM_OUTPUT`, a `RETRIEVER_CALL` result is
`RETRIEVED_CONTENT`, a `TOOL_DEF`'s parameters are `TOOL_RESULT`-adjacent
inputs, etc. A built-in registry adds framework-independent sources
(`input()`, recognized web-handler parameters, `requests`/`httpx` response
bodies). The full table lives in `specs/taint-engine.md` and growing it is a
spec PR, not an ADR.

### D3 — Unknown-call policy: under-taint, with same-module summaries

- Calls to functions **defined in the same module** get a one-level summary
  (does the return value depend on tainted parameters?), computed bottom-up
  with a fixpoint for recursion (bottom = no propagation).
- A small registry of **known propagators** (str methods, `format`, `join`,
  `json.loads`/`dumps`, container constructors, `copy`, …) propagates taint.
- **Any other call returns untainted**, even with tainted arguments.

This deliberately trades recall for precision (CLAUDE.md §1.4): an over-taint
policy makes every helper function a false-positive amplifier. The known
consequence — flows laundered through cross-module helpers are missed — is
documented, and is the reason several dataflow rules ship Medium rather than
High until cross-module taint lands (a future ADR, per `architecture.md` §4).

### D4 — Sinks are NOT the taint engine's concern

The engine answers "which labels reach this node, and via which witness
path." Rules decide what is a sink, by combining `ctx.taint` queries with
semantic tags (e.g. PLB-SEC-002: an `eval` call whose argument carries
`LLM_OUTPUT`). Rejected: a central sink registry inside the engine — it would
re-create the hand-edited central registry that ADR-0001 D6 forbids for rules.

### D5 — Provenance for messages

For every (node, label) the engine retains one deterministic witness path
(first found under sorted traversal): a list of `(line, description)` hops.
Finding messages can therefore say *"user input from `text` (line 3) reaches
the prompt via f-string (line 9)"* without any extra bookkeeping in rules.

### D6 — v1 scope boundary (explicit non-goals)

Not tracked in v1: cross-module flows; class/instance attribute state
(`self.x`); `**kwargs` through dynamic dispatch; mutation of globals through
calls; `exec`/`importlib` tricks; index-sensitive container tracking (a
container with any tainted element is tainted as a whole). `await` is
transparent. Each of these, when added, gets its own ADR; rules must set
confidence honestly against this boundary.

## Consequences

- The flagship flows (LLM output → eval/exec/shell/SQL; user input → tool-
  enabled prompt) are detectable with high precision in straight-line and
  loop code within a module.
- Some real flows are missed (cross-module helpers); this is a recorded
  recall ceiling, already noted in `backlog.md`, and the upgrade path
  (summaries across modules) does not change the rule-facing API.
- The label-set-per-node representation plus witness paths is the public
  query surface for rules (`specs/taint-engine.md` §5); changing it requires
  an ADR.
