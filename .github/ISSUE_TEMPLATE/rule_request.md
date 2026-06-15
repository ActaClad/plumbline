---
name: Rule request
about: Propose a new reliability / architecture / harness / security rule
title: "[rule] "
labels: new-rule
---

## The defect to detect

What production failure does this rule prevent? Be concrete — name the way an
agentic system actually falls over (e.g. "unbounded tool-call loop with no
iteration cap → runaway cost + hung run").

## Pillar

<!-- Pick one: Reliability & Fault Tolerance / Architecture & Agentic Maturity /
     Harness Engineering / Security & Governance -->

## What the bad pattern looks like

```python
# code that SHOULD trigger the rule
```

## What the good pattern looks like

```python
# the correct code that should NOT trigger
```

## Detection approach

- Can this be detected with **taint/dataflow** (untrusted source → dangerous
  sink), or does it need a structural/AST check? (Dataflow is strongly
  preferred; regex is the exception and must be justified.)
- Roughly how confident could detection be — could it ship **High** (≈90%+
  precision, gates builds) or should it start **Medium/Low**?

## Standards mapping (if any)

OWASP LLM Top 10 / OWASP Agentic Top 10 / NIST AI RMF / CWE — or "none".

## Willing to contribute it?

Adding a rule is an afternoon's work — see
[CONTRIBUTING.md](../../CONTRIBUTING.md) and
[docs/rule-authoring.md](../../docs/rule-authoring.md). Let us know if you'd like
to take it (we'll help).
