# ADR-0007 — `.plumbline.toml` configuration schema and CLI exit codes

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

`backlog.md` requires the config schema finalized before M2. An example file
(`.plumbline.toml.example`) exists and is treated as the draft. Open points:
discovery/precedence, strictness on unknown keys, per-rule parameters, and
the CLI exit-code contract the Quality Gate depends on.

## Decision

### D1 — Discovery and precedence

Highest wins: CLI flags → `--config PATH` → `./.plumbline.toml` at the scan
root → `[tool.plumbline]` in `pyproject.toml` at the scan root → built-in
defaults. Both file forms accept the identical schema; if both exist,
`.plumbline.toml` is used and a notice names the ignored one. Parsing uses
stdlib `tomllib` (Python ≥ 3.11 — the `tomli` conditional dependency in
`pyproject.toml` is dead and is removed).

### D2 — Schema (v1, normative)

```toml
[scan]
include = ["."]                       # roots, relative to scan root
exclude = []                          # glob patterns, in addition to defaults
respect_gitignore = true
default_excludes = true               # .venv, node_modules, build dirs, hidden dirs

[gate]
fail_on_severity = ["Blocker"]                    # any confidence
fail_on_high_confidence_severity = ["Critical"]   # High confidence only
# Default gate = union of the two lists ⇒ zero Blockers AND zero
# High-confidence Criticals (ADR-0001 D5).

[rules]
disabled = []                         # ["PLB-PRM-002"]
[rules.severity_override]             # "PLB-COST-001" = "Minor"
[rules.params]                        # per-rule thresholds, namespaced by ID
# [rules.params."PLB-MDL-003"]
# temperature_threshold = 0.3

[baseline]
file = ".plumbline-baseline.json"     # used if present; see ADR-0006

[output]
formats = ["cli"]                     # any of: cli, sarif, json, html
sarif_path = "plumbline.sarif"
json_path = "plumbline.json"
html_path = "plumbline.html"

[ai]
enrich_remediation = false            # never affects detection (ADR-0001 D2)
```

Config is materialized into a frozen `Config` dataclass; values a rule may
read arrive via `ctx.config` read-only.

### D3 — Strict validation, loud failure

Unknown sections/keys, malformed rule IDs, unknown severities, or overrides
referencing nonexistent rules are **errors** (exit code 2) with a
did-you-mean suggestion. Rationale: a silently ignored typo in
`fail_on_severity` is a silently disabled CI gate — the worst possible
failure mode for a gating tool. Rejected: warn-and-continue (acceptable for a
formatter, not for a gate).

### D4 — No Pydantic

Validation is hand-rolled over `tomllib`'s output into dataclasses. The
schema is small and stable; a runtime dependency is not justified
(CLAUDE.md §4 dependency rule).

### D5 — Exit-code contract

| Code | Meaning |
|---|---|
| 0 | Scan completed, Quality Gate passed |
| 1 | Scan completed, Quality Gate failed |
| 2 | Usage/config error (bad flags, invalid config, no such path) |
| 3 | Internal error (engine bug, rule-load failure) |

Analyzer errors on individual files (crashed detector/adapter) do **not**
affect the exit code by default; they are reported in output and SARIF
notifications. `--strict-analyzer-errors` promotes them to exit 1 for teams
that want it.

## Consequences

- The example file becomes normative; it is regenerated from the defaults in
  `config.py` by a test so docs and code cannot drift.
- CI integration is a one-liner with a stable, documented exit contract.
- Strictness implies config-schema changes are visible, versioned events —
  additive keys are fine; semantic changes need an ADR.
