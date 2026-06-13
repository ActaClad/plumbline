# ADR-0004 — Framework-adapter contract and the normalized semantic-tag model

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

`architecture.md` §5 establishes that adapters tag AST nodes with normalized
semantics so one rule covers many frameworks, and defers the contract to
`adapter-contract.md`. The contract must answer: what is the tag vocabulary,
what shape does an annotation have, how are call parameters (timeout,
temperature, tools, …) normalized when they may be set on the client, the
call, or not at all, and how do multiple adapters coexist on one file.

## Decision

### D1 — A closed, versioned tag vocabulary

`SemanticTag` is a single enum owned by core (not by adapters):
`LLM_CLIENT_CREATE, LLM_CALL, AGENT_CREATE, AGENT_INVOKE, AGENT_LOOP,
TOOL_DEF, TOOL_CALL, RETRIEVER_CALL, EMBEDDING_CALL, PROMPT_BUILD,
MEMORY_APPEND, OUTPUT_PARSE, TRACE_INIT, HTTP_CALL`. Adding a tag is a PR
that updates `specs/adapter-contract.md` (additive, no ADR needed); renaming
or removing one is an ADR. Rationale: rules program against tags — a free-form
string vocabulary would fragment per adapter and silently break rules.

### D2 — The annotation shape: `SemanticNode` with tri-state attributes

```
SemanticNode:
    tag: SemanticTag
    node: ast.AST            # the anchor node (the call, the loop, the def)
    adapter: str             # which adapter produced it
    attrs: Mapping[str, Resolved]
```

`Resolved` is a **tri-state**: `Set(value)` (statically resolved to a
constant), `Absent` (provably not configured anywhere reachable), or
`Unknown` (configured but not statically resolvable, e.g.
`timeout=settings.TIMEOUT` from another module). This tri-state is the
mechanism for confidence honesty: a High-confidence rule like PLB-RES-001
fires **only on `Absent`**, never on `Unknown`. Collapsing to two states was
rejected because it forces every parameter rule to choose between false
positives (treat Unknown as Absent) and silent gaps with no record of why.

Standard attribute keys per tag (e.g. `LLM_CALL`: `model, timeout,
max_retries, temperature, max_tokens, tools, stream`) are normative in
`specs/adapter-contract.md`.

### D3 — Client-default resolution is core machinery, not adapter code

A shared resolver (`core/values.py`) does constant folding over local and
module-scope assignments, and links call sites to the `LLM_CLIENT_CREATE`
node their receiver was bound to, merging client-level attrs into call-level
attrs (call wins). Adapters only declare *what* the framework's API looks
like; *how* values resolve is implemented once. Rationale: this logic is
subtle (it decides whether `client = OpenAI(timeout=30)` silences RES-001)
and must behave identically across adapters. A client created in another
module resolves to `Unknown` — consistent with the taint boundary (ADR-0003 D6).

### D4 — Adapter protocol and gating

An adapter is a class providing `name: str`, `priority: int`,
`trigger_imports: frozenset[str]`, and
`annotate(file_ctx) -> Iterable[SemanticNode]`. The engine invokes an adapter
on a file only when one of its trigger imports is present (cheap gating; a
file importing nothing AI-related costs near zero). All registered adapters
whose triggers match run on the file; duplicate annotations for the same
(tag, node) are resolved by adapter `priority` (framework adapters outrank
the raw-SDK adapter, since LangChain wraps the SDK underneath). Output is
sorted by `(line, column, tag)` for determinism.

### D5 — Adapter registration is an explicit core list

Unlike rules, adapters are few, core-owned, and ordered by priority — they are
registered in an explicit list in `adapters/__init__.py`. The no-central-
registry principle (ADR-0001 D6) exists to protect *contributor* throughput
on the high-volume artifact (rules); adapters are a low-volume, high-care
artifact where an explicit ordered list is clearer. Third-party adapter
discovery can be added later without breaking this.

## Consequences

- Rules are framework-agnostic by construction; adding the LangChain adapter
  in M4 widens every existing rule's coverage with zero rule changes.
- The tri-state `Resolved` becomes part of the rule-facing public contract;
  rules must handle `Unknown` explicitly, which keeps precision honest.
- `core/values.py` is added to the architecture layout (a small, deliberate
  delta to `architecture.md` §1, recorded here).
- Tag vocabulary growth is cheap; tag semantics changes are deliberately
  expensive (ADR).
