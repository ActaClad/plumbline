# ADR-0016 — Project-level adapter triggering (cross-module client detection)

- **Status:** Accepted
- **Date:** 2026-06-14
- **Deciders:** ActaClad founding team
- **Amends:** ADR-0004 §3 (the per-file adapter trigger gate)

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one.

---

## Context

ADR-0004 §3 gates an adapter on a file by that **file's** imports: the openai_sdk
adapter runs only where `openai`/`anthropic` is imported. A hardening dogfood
(H3) found this makes Plumbline blind to the **dominant real-world structure** —
a centralized client module:

```python
# app/client.py
from openai import OpenAI
client = OpenAI(timeout=30)
# app/service.py  — imports the CLIENT, not openai
from .client import client
client.chat.completions.create(model="m", timeout=None)   # NEVER detected
```

`service.py` imports `app.client`, not `openai`, so the adapter is gated off and
the LLM call — and any defect on it — is invisible. On a well-structured repo the
analyzer misses most calls. This is a silent recall gap, worse than a false
positive; per CLAUDE.md §1.4 "precision over recall" never meant "blind to how
real apps are organized."

## Decision

### D1 — Project-level trigger, opt-in per adapter

An adapter may declare `project_triggered = True`. The engine collects the union
of **all scanned files'** import roots once per run (`project_roots`) and gates a
project-triggered adapter on `(file_roots ∪ project_roots) & trigger_imports`. So
if `openai` is imported *anywhere* in the project, the openai_sdk adapter runs on
*every* file, catching cross-module calls.

Only **openai_sdk** opts in. The framework adapters (langchain, crewai) stay
**per-file** (`project_triggered = False`): they match constructs by *name* —
`@tool` decorators, `resolve_qualified` — which, run project-wide, would tag an
unrelated `@tool` decorator or need in-file imports anyway. Their cross-module
case is a different problem (D3).

### D2 — `.messages.create` stays per-file; the OpenAI-unique tails go project-wide

The precision question is whether widening the gate tags coincidental method
chains. Measured: `.chat.completions.create` and `.responses.create` /
`.embeddings.create` are unique to the OpenAI SDK shape — safe to tag project-wide.
But **`.messages.create` is also Twilio's SMS API** (`client.messages.create(to=,
body=)`), genuinely ambiguous with Anthropic. So the openai_sdk adapter emits the
OpenAI-unique tails whenever it runs, but emits `LLM_CALL` for `.messages.create`
**only when `openai`/`anthropic` is imported in that file**. A project-triggered
file with no SDK import does not get its `.messages.create` calls tagged — no
Twilio false positive.

### D3 — Named residuals (not fixed here)

- **Framework cross-module *linking*.** `from .llm import model; model.invoke()`
  still can't link `model` to its `ChatOpenAI()` construction across files, so it
  stays untagged. Cross-module symbol resolution is a separate, larger change —
  backlogged.
- **Anthropic cross-module `.messages.create`.** By D2 it is not tagged across
  modules (ambiguous with Twilio). OpenAI is the dominant case and is fixed;
  Anthropic centralized-client usage is the accepted residual.

### D4 — Precision tripwire: the existing provenance logic is correct, and tested

A cross-module `client.chat.completions.create(...)` is now tagged but its client
construction is in another file (unlinkable). The merge logic (ADR-0004 D3)
already resolves this right: an **explicit** `timeout=None` on the call →
`Known(None)` → RES-001 fires; a **bare** cross-module call → `UNKNOWN` (client
unlinkable, no provable default) → RES-001 stays silent. Both are pinned by
fixtures so this interaction can't regress.

## Consequences

- Engine becomes two-pass: parse all files → compute `project_roots` → annotate +
  taint. Determinism is unchanged (sorted files, pure functions).
- OpenAI cross-module clients (the common case) are now detected; the dogfood and
  the realistic-app FP audit are re-run to confirm no new false positive.
- The fix is scoped and measured, not a blanket un-gating; the residuals are named
  and backlogged rather than hidden.
