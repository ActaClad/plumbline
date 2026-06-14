# ADR-0015 — AI-assisted remediation boundary

- **Status:** Accepted
- **Date:** 2026-06-14
- **Deciders:** ActaClad founding team
- **Amends:** ADR-0002 (adds one optional field to `Finding`)

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one.

---

## Context

CLAUDE.md §1.1 is the constitution's first invariant: *detection is
deterministic; an LLM may ONLY generate human-readable remediation text, NEVER
decide whether a finding exists; no network in the detection path.* M8 adds the
optional AI layer. The design must make that boundary **structural**, not merely
documented — a future refactor must not be able to let AI influence a finding,
a fingerprint, or the gate.

## Decision

### D1 — Enrichment is a post-`scan()` transform in the CLI layer

`engine.scan()` is and remains AI-free: it has no import of, reference to, or
branch on the AI layer. Enrichment happens **after** `scan()` returns a final
`ScanResult` (findings fingerprinted, gate computed), in the CLI command only:

```
result = scan(...)                       # deterministic, gate decided
if config.ai.enrich_remediation:
    result = enrich_result(result, enricher)   # rewrites remediation text only
report(result)
```

This is the load-bearing invariant: **any programmatic caller of `scan()` gets
AI-free detection by construction**, not by a flag. `enrich_result` is a pure
function of `(ScanResult, Enricher)`; it returns a new `ScanResult` with
`gate`, `analyzer_errors`, and every detection field carried through unchanged —
it **never** recomputes the gate.

### D2 — The only mutable field is `remediation`; `Finding` gains one label

`enrich_result` may replace a finding's `remediation` text and nothing else. To
make the provenance visible, `Finding` gains:

```python
    remediation_is_ai: bool = False   # ADR-0015; default False
```

Set via `dataclasses.replace` on the already-fingerprinted `Finding`. It is **not**
on `FindingDraft` and **not** in `assign_fingerprints` — unlike `code_flow`
(ADR-0014), which is produced at detection time. The label is produced *after*
detection, so it is fingerprint-safe **by construction**: `compute_fingerprint`
runs before enrichment exists and never sees it. Baselines therefore never churn
on enrichment.

### D3 — Optional dependency; no key / no SDK = no-op, but not silent

The provider SDK (`anthropic`) is the `[ai]` extra, **lazy-imported inside the
enricher**, never at module top — the package imports and runs fully without it.
`build_enricher(config)` returns no enricher when: enrichment is off (default),
the extra is not installed, or the API key is absent. In the latter two cases —
*enabled but unable* — it emits a **stderr notice** ("using static remediation")
so the state is visible; "identical to disabled" means identical *detection and
exit code*, not silent.

### D4 — AI output is intentionally not byte-reproducible

With enrichment on, `remediation` text varies run-to-run — the byte-reproducibility
guarantee (ADR-0002 D3) is scoped to the deterministic detection output and to
the default (AI-off) path. Fingerprints, the gate, and baselines are stable
regardless because they exclude `remediation`. This is the one place output
determinism is conditional; documented as such.

## Consequences

- The firewall is testable and tested: a fake enricher returning *different*
  text must leave every detection field, `result.gate` (verdict + reasons), and
  the CLI exit code byte-identical to the AI-off run — only `remediation` and
  `remediation_is_ai` differ. That gate/exit equality is the §1.1 contract.
- No network in tests (fake enricher only); no test imports `anthropic`.
- "M8 works" means the firewall holds and the plumbing is correct — not that the
  LLM writes good fix text (which can't be unit-tested against a live model).
