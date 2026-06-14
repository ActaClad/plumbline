# ADR-0013 — Non-Python project evidence (for EVAL-003 / CI-gating rules)

- **Status:** Accepted (approved at the M5 review pause, 2026-06-14)
- **Date:** 2026-06-14
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> Approved by the maintainer at the M5 review: the non-Python evidence channel
> and the sanctioned grep rule are accepted into v1. Implemented by
> `core/evidence.py` (`ProjectEvidence`/`collect_evidence`), the
> `ProjectContext.evidence` accessor, the `Rule.grep_rule` marker, and
> `PLB-EVAL-003`. ADRs are immutable once Accepted — supersede to revise.

---

## Context

Every input to Plumbline so far is a Python file parsed to an AST (ADR-0009).
The plan's **PLB-EVAL-003** ("prompt/model changes not gated by evaluation in
CI") is reframed statically as: *does the repo's CI pipeline ever invoke an
evaluation/test suite?* That question cannot be answered from Python ASTs — it
requires reading CI configuration files (`.github/workflows/*.yml`,
`.gitlab-ci.yml`, `azure-pipelines.yml`, `.circleci/config.yml`, a `Makefile`,
`tox.ini`, …), which are YAML/INI/shell, not Python.

This collides with two invariants:

1. **AST-only input** (ADR-0009): adapters and rules consume Python ASTs.
2. **Dataflow over pattern-matching** (CLAUDE.md §1.2): grep-style rules are the
   *exception*, allowed only where dataflow does not apply, and must be marked.

So building CI scanning is a substrate decision, and it should not be made
silently or ahead of approval — hence this ADR.

## Decision (proposed)

### D1 — A separate, read-only "project evidence" channel

The engine gains a `ProjectEvidence` collector, distinct from the AST pipeline.
It is built once per run and exposed to PROJECT-scope rules via
`ProjectContext.evidence`. It holds:

- `repo_files: tuple[str, ...]` — every file path under the scan root (not just
  `.py`), POSIX-relative, sorted. Lets path-based signals work (`tests/`,
  `evals/`, `conftest.py`, presence of a CI directory).
- `ci_files: Mapping[str, str]` — the *text* of recognized CI config files at a
  fixed, closed set of known paths (no globbing of arbitrary YAML). Read as
  UTF-8 text; **no YAML parser dependency** (the detection path stays
  dependency-free, CLAUDE.md §4).

It does **no** semantic parsing: it is bytes + paths. Determinism: fixed path
set, sorted output, no reflection on the scanning environment (only the scanned
repo's files decide).

### D2 — EVAL-003 is a sanctioned pattern rule, marked as such

EVAL-003 scans `ci_files` text for evaluation/test invocation tokens
(`pytest`, `tox`, the eval-framework names, an `evals`/`eval` target, …). This
is explicitly a **grep-style rule** under the CLAUDE.md §1.2 exception, and its
rule metadata carries a `grep_rule = True` marker so it is never mistaken for a
dataflow rule. It fires only when: LLM/agent code exists, at least one CI file
exists, and **no** CI file contains an eval/test invocation token.

### D3 — Confidence and the EVAL-001 overlap (the approval question)

EVAL-003 ships **Medium** (advisory): CI-token matching is heuristic (a repo may
invoke evals via a script the token scan doesn't recognize), and the scan-scope
caveat (ADR-0010-adjacent) applies. The open question for the maintainer:
**EVAL-003 heavily overlaps EVAL-001.** EVAL-001 already fires when no eval suite
*exists*; EVAL-003 fires when one exists but CI doesn't *run* it. The marginal
signal is "you wrote evals but don't gate on them." If that marginal signal does
not justify a whole non-Python substrate + a sanctioned grep rule, **reject this
ADR and drop EVAL-003** — EVAL-001 carries the harness story alone.

## Consequences if accepted

- One new deterministic, dependency-free collector; PROJECT rules gain
  `ctx.evidence`. FILE rules and the AST pipeline are untouched.
- EVAL-003 is the first and (in v1) only consumer; it is a marked grep rule.
- The non-Python channel is deliberately minimal (paths + CI text) so it cannot
  grow into a second analysis engine without a further ADR.

## Consequences if rejected

- EVAL-003 is dropped from v1; the catalog row stays as roadmap. No substrate
  change. EVAL-001 + OBS-001 remain the harness pillar. This is a clean outcome.
