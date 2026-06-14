# Standards Coverage Map

This is the master matrix mapping Plumbline rules to external standards. It is
both a credibility artifact (publishable) and a contributor backlog (empty cells
are "help wanted"). Keep it in sync whenever a rule's `standards` field changes.

> Note: many **Reliability** and **Architecture** rules have NO external standard
> — that is deliberate (ADR-0001 D7). Those rows show `—`. Plumbline's own
> catalog is the de-facto reference for that surface; owning it is a moat the
> security scanners cannot contest.

## Standard identifiers used

- `OWASP-LLM01..10` — OWASP Top 10 for LLM Applications (2025)
- `OWASP-AGENTIC-*` — OWASP Top 10 for Agentic Applications (2026)
- `NIST-AI-RMF:{GOVERN|MAP|MEASURE|MANAGE}` — NIST AI Risk Management Framework
- `CWE-<n>` — Common Weakness Enumeration

## Matrix (fill `Precision` as `/benchmark` measurements land)

| Rule ID | Pillar | Severity | Confidence | Standards | Precision |
|---|---|---|---|---|---|
| PLB-RES-001 | Reliability | Blocker | High | — | 100% (2 TP / 0 FP) |
| PLB-RES-002 | Reliability | Critical | High | — | 100% (2 TP / 0 FP) |
| PLB-RES-005 | Reliability | Critical | High | — | 100% (1 TP / 0 FP) |
| PLB-RES-007 | Reliability | Critical | Medium | — | TBD |
| PLB-AGT-001 | Architecture | Blocker | High | OWASP-AGENTIC | 100% (3 TP / 0 FP) |
| PLB-AGT-002 | Architecture | Critical | High | — | 100% (1 TP / 0 FP) |
| PLB-AGT-004 | Architecture | Critical | High | — | TBD |
| PLB-MDL-001 | Reliability | Major | Medium | — | n/a (advisory) |
| PLB-MDL-002 | Reliability | Critical | High | — | TBD |
| PLB-OUT-001 | Reliability | Critical | High | — | 100% (1 TP / 0 FP) |
| PLB-OUT-003 | Reliability | Major | High | — | TBD |
| PLB-TOOL-001 | Architecture | Major | High | — | 100% (2 TP / 0 FP) |
| PLB-TOOL-002 | Architecture | Critical | High | CWE-20 | TBD |
| PLB-EVAL-001 | Harness | Major | Medium | NIST-AI-RMF:MEASURE | n/a (advisory, project-scope) |
| PLB-OBS-001 | Harness | Major | Medium | NIST-AI-RMF:MEASURE | n/a (advisory, project-scope) |
| PLB-COST-001 | Reliability | Major | High | — | 100% (2 TP / 0 FP) |
| PLB-PRM-001 | Architecture | Critical | High | OWASP-LLM01 | TBD |
| PLB-SEC-001 | Security | Blocker | High | OWASP-LLM01, OWASP-LLM02 | TBD |
| PLB-SEC-002 | Security | Blocker | High | CWE-95 | TBD |
| PLB-SEC-003 | Security | Blocker | High | CWE-78 | TBD |
| PLB-SEC-004 | Security | Blocker | High | CWE-798 | TBD |
| PLB-SEC-005 | Security | Blocker | High | CWE-89 | TBD |
| PLB-SEC-006 | Security | Critical | High | OWASP-LLM02, CWE-79 | TBD |
| PLB-SEC-007 | Security | Critical | High | CWE-918 | TBD |
| PLB-GOV-001 | Security | Critical | Medium | NIST-AI-RMF:MAP | TBD |

> Precision numbers come from `/benchmark` (regenerate `benchmark/precision.md`
> with `plumb benchmark`). Implemented rules show their measured precision;
> unimplemented rows show `TBD`.
>
> This lists the High-confidence launch set plus key mappings. Extend it to
> every rule as they are implemented — the full rule list is in
> `rule-catalog.md`. A published OWASP-coverage matrix is strong marketing;
> generate a rendered version for the docs site from this table.
