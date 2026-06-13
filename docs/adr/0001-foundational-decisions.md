# ADR-0001 — Foundational decisions: positioning, determinism, and architecture

- **Status:** Accepted
- **Date:** 2026-04-20
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Do not edit accepted ADRs except to mark them Superseded.

---

## Context

ActaClad is building an open-source static analyzer for LLM and agentic AI code,
named **Plumbline**, published as `actaclad-plumbline`. It is the design-time
companion to ActaClad's runtime platform, AgentGuard. Several existing tools
(agentic-radar, Agent Audit, ZIRAN, SkillFortify, MEDUSA) already occupy the
"AI code static analysis" space — but ALL of them are **security scanners**
mapped to the OWASP Agentic/LLM Top 10. The space is converging on security and
competing on false-positive rate.

We need to record the foundational decisions that define what Plumbline is and
how it is built, so that every later decision — human or agentic — stays
coherent with them.

## Decisions

### D1 — Positioning: reliability-led, not security-led

Plumbline's primary identity is a **reliability and architecture analyzer**. Its
headline question is *"will this agentic system fall over in production?"* The
four pillars, in priority order, are:

1. Reliability & Fault Tolerance
2. Architecture & Agentic Maturity
3. Harness Engineering (the engineering scaffold around the model: evaluation
   harnesses, verification nodes, ground-truth checks, observability)
4. Security & Governance

Security is covered competently but is explicitly NOT the headline. Rationale:
the security lane is crowded and commoditized by a shared OWASP taxonomy;
the reliability/architecture/harness lane is unclaimed by static analysis and
maps to a fear buyers already have. It also plays to the founder's strength
(a 20-year software architect) and connects cleanly to AgentGuard's runtime story.

### D2 — Detection is deterministic; AI is only for remediation

The detection engine is pure static analysis (AST + dataflow). Identical input
must yield identical findings, with no network/clock/randomness in the detection
path. An LLM may be used ONLY to generate human-readable remediation text at
output time. Rationale: a reproducible analyzer can gate a build and be trusted;
LLM-as-detector produces non-determinism, hallucination, and high false-positive
rates (it reasons over variable names, not execution logic). The effective
pattern is neuro-symbolic: deterministic backbone, LLM only at the edges.

### D3 — Dataflow (taint) engine is the core, built first

The substrate is a taint tracker (untrusted sources → dangerous sinks). It is
built BEFORE any rules, because the flagship detections (untrusted input → tool-
enabled prompt; LLM output → eval/exec/shell/SQL) are trivial with it and
impossible without it. Pattern-matching rules are the exception, not the norm.

### D4 — Confidence levels and the no-noise rule

Every finding is High / Medium / Low confidence. High requires a measured
precision (~90%+) recorded in `/benchmark`; otherwise the rule ships as Medium
or Low. Low-confidence findings are excluded from scoring. Rationale: false
positives are what kill linters; we optimize for trust over coverage.

### D5 — Quality Gate is the CI mechanism; scores are dashboards

Teams wire a pass/fail Quality Gate into CI (default: zero Blockers AND zero
High-confidence Criticals). Pillar scores and the composite **Readiness Score**
are stakeholder roll-ups only. The composite is NEVER called "Trust Score" —
that term and "Trust Profile" belong exclusively to AgentGuard, which Plumbline
feeds rather than duplicates.

### D6 — Rule-plugin architecture with convention-based discovery

Every rule is a self-contained module (ID `PLB-<CAT>-<NNN>`) with metadata, a
detector function, a remediation template, and a vulnerable+clean fixture pair.
Rules are discovered by convention, not via a hand-edited central registry, so
contributors never hit a merge-conflict bottleneck. One rule = one detector +
two fixtures + tests; no rule exists without a failing fixture.

### D7 — Standards-grade output

SARIF 2.1.0 output is mandatory (consumed by GitHub code scanning, GitLab,
IDEs). Every rule maps to external standards where they exist (OWASP LLM Top 10
2025, OWASP Agentic Top 10 2026, NIST AI RMF, CWE). For reliability/architecture
rules where no external standard exists, Plumbline's own published catalog
becomes the de-facto reference — an asset security scanners cannot contest.

### D8 — Build order: substrate → one rule end-to-end → reliability core → rest

Do not build rules first. Skeleton + Finding model + AST + one adapter → taint
engine → `PLB-RES-001` end-to-end → reporters + gate → reliability core →
more adapters → harness pillar → security pillar → scoring → AI remediation →
(Phase 2) trace ingestion. Security ships AFTER the differentiated pillars.

### D9 — License and ecosystem identity

Apache-2.0. Package `actaclad-plumbline`; CLI verb `plumb`; repo
`actaclad/plumbline`. The `actaclad-` prefix mirrors `actaclad-agentguard` and
sidesteps bare-name collisions on PyPI.

## Consequences

- The rule catalog and build backlog are weighted toward reliability/
  architecture/harness; security is competent but not dominant.
- Contributors and the coding agent have a clear, stable contract and ordering.
- The deterministic constraint forbids tempting shortcuts (e.g., "just ask an
  LLM if this code is risky") in the detection path.
- The funnel to AgentGuard is structural (design-time → runtime) rather than
  promotional, which protects Plumbline's standalone credibility.
- Naming and scoring choices are constrained to avoid diluting AgentGuard's
  Trust Profile brand.
