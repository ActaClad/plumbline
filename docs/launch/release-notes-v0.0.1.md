# Plumbline v0.0.1 — first public release

> **Draft — GitHub Release body for tag `v0.0.1`.** Paste into the release on
> github.com/ActaClad/plumbline (or `gh release create v0.0.1 -F` this file).
> Numbers here are sourced verbatim from `CHANGELOG.md` and `README.md` — keep
> them in sync if either changes. Publishing this release triggers `publish.yml`;
> see the trusted-publishing note at the bottom before you publish.

**Your agent didn't get hacked. It fell over.**

Plumbline is an open-source **static analyzer for the reliability of LLM and
agentic Python**. Every AI-code scanner asks *"is this dangerous?"* — prompt
injection, the OWASP LLM Top 10. But most agentic systems don't break because
they were attacked; they break because they were engineered badly: a model call
with no timeout that hangs the worker pool, no retry on a 429, a `json.loads()`
on raw model output that crashes on the first markdown-fenced response, an agent
loop with no iteration cap that burns tokens until someone notices. Those are
**reliability and architecture defects**, and no static analyzer was looking for
them. This one does — at design time, from the source alone.

```
pip install actaclad-plumbline
plumb scan ./your-agent
```

## What's in this release

**32 rules across all four pillars** — 12 High-confidence (gating) and 20
advisory — weighted to the differentiated wedge: Reliability and Architecture
lead, ahead of Security. The full ~60-rule taxonomy in the catalog is the
published contributor roadmap. High-confidence rules carry a *measured* precision
number in [`/benchmark`](../../benchmark); advisory rules graduate to High only
after a real-repo precision pass.

**Deterministic detection you can wire into CI.** The engine is pure static
analysis — AST plus a taint/dataflow tracker, no LLM in the detection path, no
network, no clock, no randomness. Same code in, byte-identical findings out; it
runs fully offline. An optional LLM step rewrites only the human-readable fix
text — it never decides whether a finding exists, and it's off by default.

**False positives are the enemy.** Only High-confidence rules can fail a build,
and a rule ships High only with a measured precision behind it. A tri-state
resolver (`Known` / `ABSENT` / `UNKNOWN`) stays silent rather than guess when it
can't prove a defect is present.

**Standards-grade output.** SARIF 2.1.0 (schema-validated, with taint
`codeFlows` — drops straight into the GitHub Security tab), JSON, a
self-contained branded HTML report (`plumb scan --open`), and a pass/fail
**Quality Gate** for CI. Findings map to OWASP LLM/Agentic Top 10, NIST AI RMF,
and CWE where a standard exists.

### Rules by pillar

- **Reliability** — `RES-001/002/005` (timeout, retries, swallowed errors),
  `OUT-001` (unguarded JSON parse), `COST-001` (no max_tokens) gate;
  `OUT-002`, `MDL-001/002/003`, `RES-010` (leaked streamed connection) advisory.
- **Architecture** — `AGT-001/002` (agent-loop cap / termination across three
  frameworks), `TOOL-001` (untyped tool) gate; `TOOL-003`, `PRM-003`, `AGT-008`
  (AutoGen team with no turn cap) advisory.
- **Harness** — `EVAL-001/003`, `OBS-001` — the "flying blind" rules.
- **Security** — `SEC-002/003/005/006` (eval/exec, shell, SQLi, XSS) gate;
  `SEC-004` (hardcoded secret, downgraded to advisory after real-repo
  validation), `SEC-007`, `GOV-001/002`, and the new **MCP category**
  (`MCP-001` no-auth server, `MCP-003` wildcard OAuth scopes) advisory.
- **Reasoning-model configuration** (ADR-0018) — `MDL-006/007/008` catch config
  that is a guaranteed HTTP 400 on reasoning models.

## Install & run

```bash
pip install actaclad-plumbline   # Python 3.11+ to run; scans code of any version
plumb scan ./app                 # human-readable findings + Readiness Score
plumb scan ./app --sarif out.sarif   # upload to the GitHub Security tab
plumb scan ./app --open          # write + open the HTML report
plumb rules                      # list loaded rules
```

Wire it into CI with the five-line [Plumbline Action](../../action.yml) or the
[`pre-commit`](https://pre-commit.com) hook (`id: plumbline`). See
[`docs/ci-integration.md`](../ci-integration.md).

## Honest limits (v0.0.1)

- **Python only.** Adapters cover the raw OpenAI/Anthropic SDKs,
  LangChain/LangGraph, and CrewAI. Other stacks are invisible until an adapter
  exists — and we tell you when a file produced zero semantic nodes.
- **Taint is intra-procedural by design** — it misses some cross-function flows.
  A precision choice, not an oversight.
- **32 of ~60 catalogued rules are implemented.** The rest is a public roadmap,
  deliberately weighted toward reliability and architecture over security.

Apache-2.0. Every rule open — no held-back "pro" pack. If you hit a false
positive, that's the most valuable bug you can file; it becomes a fix plus a
regression test, in public.

**Full detail:** [`CHANGELOG.md`](../../CHANGELOG.md) ·
**Repo:** github.com/ActaClad/plumbline

---

### Maintainer note — before publishing this release

Publishing a GitHub Release for `v0.0.1` triggers `publish.yml`, which builds and
publishes to PyPI via **trusted publishing (OIDC)**. This only works if the PyPI
trusted publisher is configured **first** (see
[`docs/trusted-publishing.md`](../trusted-publishing.md)). `0.0.1` was
hand-uploaded to claim the name, so the publish step will `skip-existing` and
no-op gracefully — which makes publishing this release a safe end-to-end test of
the pipeline. Cut real releases (`0.0.2`+) the same way once the publisher is set.
