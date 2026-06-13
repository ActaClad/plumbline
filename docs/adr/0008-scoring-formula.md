# ADR-0008 — Pillar-score and Readiness Score formula

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

`architecture.md` §7 requires the exact formula in a dedicated ADR before
`scoring/` is implemented. Constraints: Low-confidence findings are excluded
(ADR-0001 D4); the score is a dashboard, never the CI mechanism (D5); the
composite is the **Readiness Score**, never "Trust Score" (CLAUDE.md §1.10).

## Decision

### D1 — Pillar score: capped linear penalty

For each pillar, over **non-suppressed findings of High or Medium confidence**
belonging to that pillar:

```
penalty(f)   = severity_weight(f.severity) × confidence_factor(f.confidence)
pillar_score = max(0, round(100 − Σ penalty(f)))
```

| Severity | weight |   | Confidence | factor |
|---|---|---|---|---|
| Blocker  | 25 |  | High   | 1.0 |
| Critical | 10 |  | Medium | 0.4 |
| Major    | 3  |  | Low    | excluded |
| Minor    | 1  |  |        |        |
| Info     | 0  |  |        |        |

Severity/confidence used are the **effective** values after config overrides
(ADR-0002 D1); suppressed (baselined/inline-ignored) findings are excluded
(ADR-0006).

Rejected alternatives: density normalization per KLOC (fairer across repo
sizes but unexplainable in v1 without telemetry from real repos — recorded in
`backlog.md` as a candidate v2, which would supersede this ADR);
SonarQube-style letter ratings (hides information; a 0–100 number plus the
gate communicates more); multiplicative decay (`100 × Π(1−p)`) (opaque — no
user can recompute it mentally; the linear sum is auditable by hand).

### D2 — Readiness Score: weighted mean of pillar scores

```
Readiness = round(0.35·Reliability + 0.25·Architecture
                + 0.20·Harness     + 0.20·Security)
```

Weights are the suggested values from `architecture.md` §7, hard-coded in
v1 (not user-configurable — a configurable composite is incomparable across
repos and invites gaming; revisit only with evidence).

### D3 — Not-applicable beats a misleading 100

If a scan finds **zero semantic nodes** (no LLM/agent code detected), all
pillar scores and the Readiness Score are reported as **N/A**, not 100. A
Django monolith with no AI code is not "100/100 production-ready agentic
code" — reporting that would be the score equivalent of a false positive.
JSON/SARIF represent N/A as `null`; the CLI prints "no LLM/agent code
detected."

### D4 — Worked example (normative test vector)

A repo scan yields, after suppression filtering:

| # | Rule | Pillar | Severity | Confidence | penalty |
|---|---|---|---|---|---|
| 1 | PLB-RES-001 | Reliability | Blocker | High | 25 × 1.0 = 25 |
| 2 | PLB-RES-002 | Reliability | Critical | High | 10 × 1.0 = 10 |
| 3 | PLB-RES-008 | Reliability | Major | Medium | 3 × 0.4 = 1.2 |
| 4 | PLB-AGT-001 | Architecture | Blocker | High | 25 × 1.0 = 25 |
| 5 | PLB-AGT-005 | Architecture | Major | Medium | 3 × 0.4 = 1.2 |
| 6 | PLB-OBS-001 | Harness | Major | High | 3 × 1.0 = 3 |
| 7 | PLB-RAG-003 | Architecture | Major | **Low** | excluded |
| 8 | PLB-SEC-004 | Security | Blocker | High | 25 × 1.0 = 25 |

```
Reliability  = max(0, round(100 − 36.2)) = 64
Architecture = max(0, round(100 − 26.2)) = 74
Harness      = max(0, round(100 − 3))    = 97
Security     = max(0, round(100 − 25))   = 75

Readiness    = round(0.35·64 + 0.25·74 + 0.20·97 + 0.20·75)
             = round(22.4 + 18.5 + 19.4 + 15.0) = round(75.3) = 75
```

This table is encoded as a unit-test vector; the implementation must
reproduce it exactly.

## Consequences

- Scores are hand-auditable: a user can recompute any pillar from the
  findings list and this table.
- Four High-confidence Blockers zero a pillar — intentional; the score is a
  dashboard and a zeroed pillar is a legitimate "this is on fire" signal.
- Weight or formula tuning after real-repo telemetry is a superseding ADR,
  and the JSON output carries `"scoring_model": "adr-0008"` so consumers can
  detect the change.
