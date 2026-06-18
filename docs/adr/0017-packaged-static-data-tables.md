# ADR-0017 — Packaged static data tables for data-driven rules

- **Status:** Accepted
- **Date:** 2026-06-18
- **Deciders:** Plumbline core
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one.

---

## Context

PLB-MDL-002 (deprecated/sunset model identifier) needs to know which model ids
are dead. That knowledge is a *list*, not logic: it changes on the providers'
schedule, not ours, and it grows over time. Two forces are in tension:

- **Determinism + no-network (CLAUDE.md §1.1).** The detection path may not make
  network calls, so the list cannot be fetched at scan time. Running Plumbline
  twice on the same code must give identical findings regardless of connectivity.
- **Maintainability.** The list will need periodic updates. Burying it inside a
  detector's source mixes volatile data with stable logic and makes review noisy.

This is the first rule whose correctness depends on a curated dataset rather than
on code structure, so it sets the pattern for any future data-driven rule (e.g.
a known-vulnerable-dependency list, a PII-field dictionary).

## Decision

Data-driven rules read from **versioned, in-repo Python literal modules** under
`src/plumbline/data/`, imported normally. No runtime fetch, no external file
format, no packaging-data concerns (a plain importable module ships with the
wheel automatically).

- MDL-002's list lives in `plumbline/data/deprecated_models.py` as
  `DEPRECATED_MODELS: dict[str, str]` (exact-id → human deprecation note).
- Matching is **exact string equality** against a call's *resolved* `model=`
  value (via the adapter's tri-state `Known` attr), never a substring/prefix —
  a prefix match would flag live models (`gpt-4o` contains no dead id, but a
  naive `startswith` on `gpt-4` would catch it). Exact-match keeps precision the
  priority (CLAUDE.md §1.4).
- The table is a **manually-curated snapshot**. Its refresh process (and the
  option to later generate it from providers' published deprecation pages in a
  *build* step, never at scan time) is tracked in `docs/backlog.md`.

Confidence: MDL-002 ships **Medium/advisory** despite deterministic detection,
because its real-world precision has not been measured on real repos (CLAUDE.md
§1.3). It graduates to High only after a real-repo precision pass — the same
discipline applied to every other rule. The data-table mechanism itself does not
confer High confidence.

## Consequences

- **Easier:** adding/curating deprecations is a one-line dict edit with a clear
  diff; the detector logic stays tiny and stable; the list is unit-testable and
  reviewable independently of the rule.
- **Constrained:** *provided every entry is a genuinely-retired id*, the list can
  only go stale in the *safe* direction — a missed deprecation is a recall gap,
  never a false positive. The bar for adding an id is therefore "provably
  retired/sunset," never "looks old": a wrongly-listed *live* model would be a
  flat false positive on working code (the cardinal sin, CLAUDE.md §1.4).
- **Follow-up:** a periodic-refresh process for the table (backlog). Any future
  data-driven rule follows this same pattern: a literal module under
  `plumbline/data/`, exact-match consumption, no runtime I/O.
- **New invariant:** detection-path data tables live in `plumbline/data/` as
  importable literals and are never fetched at runtime.
