# ADR-0018 — Reasoning-model configuration rules (MDL-006/007/008)

- **Status:** Accepted
- **Date:** 2026-07-04
- **Deciders:** Durai (CTO)
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one.

---

## Context

Reasoning/thinking models (OpenAI o-series and GPT-5; Anthropic Opus 4.7/4.8 and
Fable-5) changed the call contract in ways that make previously-valid code fail
**hard, on every call**, with an HTTP 400:

- On these models the **sampling parameters** `temperature`/`top_p`/`top_k` are
  *removed* — passing any of them is rejected outright (not merely ignored).
- OpenAI reasoning models require **`max_completion_tokens`**, not `max_tokens`,
  on Chat Completions.
- On Anthropic models that *do* accept extended-thinking `budget_tokens`
  (pre-4.7, incl. 4.6), the budget has hard constraints: `budget_tokens < max_tokens`,
  `budget_tokens >= 1024`, `temperature == 1`, and no `top_k`.

These are the most on-brand defect class Plumbline can carry: deterministic,
statically detectable at a literal call site, ~100% precision (a guaranteed
production outage, not a heuristic), and — per the launch research — genuinely
uncovered by any competing analyzer. The param legality is **model-generation
dependent**, so a naive "temperature on a reasoning model is bad" rule would
false-positive across generations. A decision is needed on how to encode that
dependence without a network call (principle #1: detection is deterministic,
offline).

## Decision

Ship the class as **three sibling rules** — one per distinct failure mode — over
a **shared, packaged static data table** (`data/reasoning_models.py`), following
the exact ADR-0017 pattern already used by MDL-002's `DEPRECATED_MODELS`:

- **PLB-MDL-006 — removed sampling param present.** Table `SAMPLING_UNSUPPORTED:
  dict[model_id -> frozenset[param]]`. Fires when a call's *resolved* `model` (so a
  pinned-variable model is caught, per MDL-002) is in the table AND one of the
  removed params is **provably present** as an explicit keyword on the call node.
- **PLB-MDL-007 — thinking-budget constraint violated** (Anthropic models that
  accept `budget_tokens`): literal AST comparison of `budget_tokens`/`max_tokens`/
  `temperature`/`top_k`.
- **PLB-MDL-008 — OpenAI reasoning model uses `max_tokens`** instead of
  `max_completion_tokens`.

Three rules, not one multiplexed detector, because the rule-plugin contract is
"one ID = one module + its own fixtures" (discovery by convention, ADR-0005);
sharing the *table*, not the *detector*, keeps that contract intact and lets each
rule carry its own precise message, standards mapping, and bad/good fixtures. The
model sets are disjoint per failure mode, so the three never double-fire on the
same call.

**Precision mechanism (the load-bearing choice):** MDL-006 detects param
**presence from the call's explicit `ast.keyword` list**, not from a resolved
value. A param spread via `**kwargs` is therefore *not* flagged — we can only
prove presence for an explicit keyword, and "provable presence" is what keeps
precision at ~100% (principle #4, false positives are the enemy). The model id is
still read from the adapter-resolved `model` attr so a pinned-variable model
(`M = "o3"; create(model=M)`) is caught.

**Model list is precision-over-recall.** As with `DEPRECATED_MODELS`, the table
lists only exact ids we are confident reject the param; a missing id is a recall
gap (safe), a wrong id is a false positive (not). The table is a manually-curated
snapshot; keeping it current is a maintenance task tracked in `docs/backlog.md`.

**Confidence:** all three ship **Medium/advisory** first (per CLAUDE.md §1.3 and
the public rule-stability promise — a rule gates only after a measured
`/benchmark` precision number), even though the underlying error is a hard 400.
Severity is **Critical** (an every-call outage), so they surface prominently
without breaking a CI gate on adoption.

## Consequences

- **Easier:** a new marquee, market-differentiated reliability rule class with no
  network dependency; the same table pattern extends as models evolve.
- **Harder / new maintenance:** `data/reasoning_models.py` must be refreshed as
  providers ship models (backlog item, same class as `DEPRECATED_MODELS`). A
  wrongly-listed id is a false positive on working code — the bar to add an id is
  "provably rejects the param," never "looks like a reasoning model."
- **Constrained:** these rules read param presence from the call node's explicit
  keywords; they intentionally do not reason about `**kwargs` spreads (silent, not
  a false positive). Graduating any of them to High requires a `/benchmark`
  precision measurement first.
- MDL-006 lands in this ADR's first increment; MDL-007/008 follow, sharing the
  table.
