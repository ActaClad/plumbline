# ADR-0012 — Derived semantics, agent-loop properties, and framework defaults

- **Status:** Accepted
- **Date:** 2026-06-14
- **Deciders:** ActaClad founding team
- **Supersedes:** none
- **Amends:** the AGENT_LOOP row of `adapter-contract.md` §5 (see D1)

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

M4 adds the LangChain/LangGraph and CrewAI adapters and the first agent
control-flow rules (AGT). Three problems surface that the existing contract
does not answer:

1. **Cross-cutting tags.** A *hand-rolled* agent loop is a `while`/`for` whose
   body contains an `LLM_CALL` — and that call may be tagged by **any** adapter
   (openai_sdk, langchain, …). The current pipeline runs each adapter on the
   raw `SourceTree` in isolation (`collect_semantics`), so no single adapter can
   see "is there an LLM_CALL inside this loop, regardless of who tagged it."
   `adapter-contract.md` §5 provisionally placed `AGENT_LOOP` in the openai_sdk
   pattern table; that is wrong for a mixed- or non-OpenAI loop. This is a
   spec-vs-spec conflict and must be resolved, not papered over (CLAUDE.md §2).

2. **One `bounded` flag is two properties.** AGT-001 ("no max-iteration cap")
   and AGT-002 ("no termination/exit condition") read *different* signals. A
   `while True:` with a goal-based `break` and no counter **terminates**
   (not an AGT-002 defect) but has **no hard cap** (an AGT-001 defect).
   Collapsing both into one flag makes one of the two rules wrong.

3. **Framework defaults repeat the RES-001 trap.** LangChain's `AgentExecutor`
   ships a finite `max_iterations` default; LangGraph bounds runs by a default
   `recursion_limit`; CrewAI agents ship a finite `max_iter`. A *bare*
   `AgentExecutor(...)` is therefore **bounded**. Firing AGT-001 on a missing
   `max_iterations` keyword is exactly the false-positive class ADR-0004 D3
   killed for timeouts — it must be killed the same way here.

## Decision

### D1 — A derived-semantics pass computes cross-cutting tags

After `collect_semantics` runs every adapter and before the `SemanticIndex` /
taint are built, the engine runs one **derivation pass**
(`core/derive.py::derive_semantics(tree, collected) -> list[SemanticNode]`).
It is a pure, deterministic function of the AST plus the already-collected
semantic nodes; it does no I/O and calls no adapter. Its output is appended to
the collected nodes before indexing.

v1 derives exactly one tag: **`AGENT_LOOP`**. `AGENT_LOOP` is therefore
**removed from the openai_sdk pattern table** (`adapter-contract.md` §5,
amended here) and is *never* emitted by an adapter — it is framework-independent
by construction, which is precisely what lets one AGT rule cover every
framework's hand-rolled loops.

Rejected: making adapters depend on each other's output (ordering coupling, no
clean contract); a per-adapter loop detector (breaks on mixed-client loops —
the exact thing the derivation pass exists to handle).

### D2 — `AGENT_LOOP` population is narrow on purpose

A `while`/`for` is tagged `AGENT_LOOP` only if its body (excluding nested
function/class defs) **transitively contains at least one `LLM_CALL`**. A loop
with no model call in it is not an agent loop and is never tagged — narrowing
the population is what keeps AGT precision high (CLAUDE.md §1.4). The anchor is
the loop statement node.

### D3 — Two independent loop properties, each tri-state

`AGENT_LOOP` carries two attributes, each `Known(True)` / `Known(False)` /
`UNKNOWN`. High-confidence AGT rules fire only on `Known(False)` (never on
`UNKNOWN` — ADR-0004 D2).

- **`has_iteration_cap`** — is there a hard bound on iteration count?
  - `for` over `range(...)` or a literal list/tuple/set → `Known(True)`.
  - `for` over anything else (an arbitrary name, a generator) → `UNKNOWN`.
  - `while` whose test is a truthy constant (`while True:`, `while 1:`) **with
    no integer counter that is incremented in the body and referenced by the
    test or a guarded `break`** → `Known(False)`.
  - `while` with such a counter pattern → `Known(True)`.
  - any other `while` → `UNKNOWN`.

- **`has_goal_exit`** — can the loop terminate on a goal/condition?
  - any `for` loop → `Known(True)` (the iterator exhausts).
  - `while` with a non-constant test → `Known(True)` (the test can go false).
  - `while` with a truthy-constant test and a reachable `break`/`return` in the
    body (not inside a nested def) → `Known(True)`.
  - `while` with a truthy-constant test and **no** reachable `break`/`return`
    → `Known(False)`.

Worked cases (these are fixture-backed):

| Loop | `has_iteration_cap` | `has_goal_exit` | AGT-001 | AGT-002 |
|---|---|---|---|---|
| `while True:` … no break | `Known(False)` | `Known(False)` | fires | fires |
| `while True:` … `if done: break` | `Known(False)` | `Known(True)` | fires | silent |
| `for _ in range(MAX):` … | `Known(True)` | `Known(True)` | silent | silent |
| `while n < MAX:` … `n += 1` | `Known(True)` | `Known(True)` | silent | silent |

### D4 — Framework constructors resolve `max_iterations` against a known default

`AGENT_CREATE` (emitted by the langchain/crewai adapters) resolves
`max_iterations` with the same provenance machinery the openai_sdk adapter uses
for `timeout` (ADR-0004 D3):

- explicit keyword present → that value, `max_iterations_source="explicit"`;
- absent **and** the constructor has a known finite framework default →
  `Known(<default>)`, `max_iterations_source="framework_default"`;
- absent **and** no known default / unresolvable → `UNKNOWN`.

AGT-001 fires on `AGENT_CREATE` only when `max_iterations` is `Known(None)`
(an explicit cap-removal) — never on bare construction. **The rule depends only
on a finite default *existing*, not on its exact numeric value.** This insulates
the analyzer from version churn in the frameworks' default numbers: we record
the value we believe current (and the version assumption, in the adapter spec),
but correctness does not rest on it. The version assumption is stated in
`adapter-contract.md` §8/§9 and surfaced at the M4 review.

## Consequences

- One AGT-001 detector consumes two tags (`AGENT_CREATE`, `AGENT_LOOP`) and
  fires identically across LangChain, CrewAI, and hand-rolled loops — the M4
  DoD ("one rule, three frameworks") is met by construction.
- `AGENT_LOOP` boundedness is a **heuristic**, unlike the syntactic M3 signals
  (`timeout=None`). AGT-001/002 therefore ship at the confidence their measured
  `/benchmark` precision earns — at **Medium** until a corpus that stresses the
  false-positive surface (legitimate `range(MAX)` loops, counter-guarded
  `while`, goal-break loops) clears 90%, then promoted, exactly as RES-001 was.
- The derivation pass is a new deterministic stage; it joins the double-run
  byte-equality guarantee and is contained as an `AnalyzerError` on crash like
  every other stage (CLAUDE.md §4).
