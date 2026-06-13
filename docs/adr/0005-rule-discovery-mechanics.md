# ADR-0005 — Rule discovery mechanics

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

ADR-0001 D6 and the rule-plugin contract require convention-based discovery —
adding a rule must never mean editing a central registry. The mechanics
(import strategy, validation, failure behavior, third-party rules) are
undecided.

## Decision

### D1 — Discovery = walk + import + collect `RULE`

At engine startup, `rules/base.py` walks `plumbline.rules` with
`pkgutil.walk_packages`, imports every module **in sorted module-name
order**, and collects each module-level `RULE` attribute that is a `Rule`
instance. Modules without a `RULE` attribute (e.g. shared helpers per
category) are skipped silently. Discovery is pure-Python import — no
filesystem scanning of source files, so it works identically from a wheel,
an editable install, or a zipapp.

Rejected: file-glob + `importlib.util.spec_from_file_location` (breaks under
zipimport and confuses mypy), and decorator-based registration with import
side effects spread across files (harder to reason about than one collector).

### D2 — Validation is a hard, loud failure at load time

At collection time the loader enforces, raising `RuleLoadError` (which aborts
the run with exit code 3 — a broken rule set must never half-run):

1. **ID format** `PLB-<CAT>-<NNN>` with a known category code.
2. **ID ↔ module-name coherence**: `PLB-RES-001` must live in a module named
   `plb_res_001`. This makes grep, fixtures (`fixtures/PLB-RES-001/`), and
   tests line up mechanically and prevents copy-paste ID drift.
3. **Duplicate IDs** anywhere in the walk are a hard error.
4. **Metadata completeness**: non-empty title, why_it_matters, remediation;
   valid severity/confidence/pillar; category code consistent with the ID.

A shared meta-test additionally asserts every discovered rule has at least
one `bad_*` and one `good_*` fixture under `fixtures/<ID>/` — the
"no rule without a failing fixture" principle enforced mechanically.

### D3 — Rules declare their scope

Each `Rule` declares `scope: Scope.FILE | Scope.PROJECT` (ADR-0010). The
loader indexes rules by scope so the engine can run file-scope rules per file
and project-scope rules once per run.

### D4 — Third-party rule packages: deferred, but not precluded

v1 discovers only `plumbline.rules.*`. An entry-point group
(`plumbline.rules`) for external rule packages is recorded in `backlog.md`;
the loader's collect-and-validate pipeline is written so an additional module
source can be appended without changing the rule contract.

## Consequences

- A contributor adds a rule by adding one module + fixtures + a test; nothing
  central changes; merge conflicts between rule PRs are structurally
  impossible.
- ID/module coherence gives tooling (benchmark harness, fixture loader,
  `plumb rules`) a single derivable mapping.
- Load-time validation means a malformed rule fails CI in the rule author's
  PR, not at a user's scan time.
- Import cost of the full rule tree is paid once per run; with ~40 small
  modules this is negligible.
