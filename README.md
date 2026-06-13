<!-- Plumbline README. Keep positioning-first. Update the badges/links when the
     repo and PyPI package are live. -->

<div align="center">

# Plumbline

**The reliability and architecture analyzer for LLM & agentic systems.**

*A plumb line tells a builder whether a structure is true. Plumbline tells you
whether your agent code is built to survive production.*

`pip install actaclad-plumbline`

[Quickstart](#quickstart) · [What it checks](#what-it-checks) · [Why Plumbline](#why-plumbline) · [Contributing](CONTRIBUTING.md) · [by ActaClad](https://actaclad.com)

</div>

---

## The problem

Agentic systems demo beautifully and break invisibly. They rarely fail because
they were attacked — they fail because they were **badly engineered**: a runaway
agent loop with no iteration cap, no fallback when a provider returns 429, an
`eval()` on model output that dies on the first unexpected token, unbounded
memory growth, a silent model swap that changed behavior, no verification step
so an early error rides all the way to the final answer.

AI-assisted coding makes this worse, not better. More agent code is being
written, faster, and reviewed less per line — and studies show AI-generated code
carries *more* of these defects, not fewer.

Existing static analyzers for AI code are all **security scanners**. They ask
*"is this code dangerous?"* That leaves an entire dimension unchecked.

## What Plumbline does

**Plumbline asks a different question: *will this system fall over in
production?*** It statically analyzes LLM and agentic code for reliability,
architecture, harness-engineering, and security defects — then tells you exactly
what, where, why it matters, and how to fix it.

It is **not a style linter.** It does taint/dataflow analysis to reason about
real properties of your code — does untrusted input reach a tool-enabled prompt,
is there a fallback path, is the agent loop bounded — not whitespace and naming.

Detection is **fully deterministic**: same code, same findings, every run.
Safe to gate a build on. (An optional AI layer enriches *fix suggestions* only —
never the detection itself.)

## What it checks

Four pillars, in priority order:

| Pillar | Examples of what it catches |
|---|---|
| **Reliability & Fault Tolerance** | missing timeouts/retries/fallbacks, bare excepts swallowing failures, unbounded memory, non-idempotent retried side effects, no output cap |
| **Architecture & Agentic Maturity** | unbounded agent loops, no termination condition, no verification/self-critique node, untyped tools, RAG context overflow, prompt assembly anti-patterns |
| **Harness Engineering** | no evaluation suite, no golden datasets / ground-truth checks, model/prompt changes not gated by evals, no tracing or correlation IDs |
| **Security & Governance** | untrusted input into tool-enabled prompts, LLM output into eval/exec/shell/SQL, hardcoded secrets, unsanitized output rendering, PII into prompts |

Full catalog: [`docs/specs/rule-catalog.md`](docs/specs/rule-catalog.md).
Every rule maps to OWASP LLM Top 10, OWASP Agentic Top 10, NIST AI RMF, or CWE
where applicable.

## Quickstart

```bash
pip install actaclad-plumbline

# scan a project — the Quality Gate runs by default
# (exit 1 on any Blocker or High-confidence Critical), so it's CI-ready as-is
plumb scan ./my-agent-app

# emit SARIF for GitHub code scanning / IDEs (and/or JSON)
plumb scan ./my-agent-app --sarif plumbline.sarif --json plumbline.json

# adopt incrementally on an existing repo: accept today's findings, gate on new ones
plumb baseline ./my-agent-app        # writes .plumbline-baseline.json
plumb scan ./my-agent-app            # only *new* findings fail the gate

# list loaded rules
plumb rules
```

Wiring it into CI takes one job — see [`docs/ci-integration.md`](docs/ci-integration.md).

Supported today: Python, with adapters for the raw OpenAI/Anthropic SDKs,
LangChain/LangGraph, and CrewAI. (More frameworks and languages on the roadmap —
[contributions welcome](CONTRIBUTING.md).)

## Output

Each finding tells you:

- **what** — the defect, with a stable rule ID (`PLB-RES-001`)
- **where** — file and line
- **severity & confidence** — Blocker/Critical/Major/Minor/Info × High/Medium/Low
- **why it matters** — the concrete production failure it leads to
- **how to fix it** — a specific remediation, with a bad/good example
- **standard** — the OWASP/NIST/CWE reference where one applies

Plus a **Readiness Score** per pillar (a stakeholder roll-up — the pass/fail
Quality Gate is what you wire into CI).

## Why Plumbline

- **Reliability-first, not security-only.** The unclaimed lane, and the one that
  maps to a failure you've actually seen in production.
- **Deterministic and trustworthy.** Reproducible findings you can gate a build
  on. Low false-positive rate is a first-class design goal, measured in
  [`/benchmark`](benchmark/).
- **Actionable.** Every finding ships with a fix, not just a flag.
- **Standards-grade.** SARIF 2.1.0; OWASP/NIST/CWE mappings.
- **Genuinely open.** Apache-2.0. The rule catalog is a community asset; adding
  a rule takes an afternoon.

## Design-time and runtime: Plumbline + AgentGuard

Plumbline is the **design-time** half of a pair. It checks your code is sound
*before* it ships. [**AgentGuard**](https://actaclad.com), ActaClad's runtime
trust platform, confirms your system is trustworthy *in production* —
observability, evaluation, security, and audit-ready governance. Plumbline's
reliability findings are the static precursors of the signals AgentGuard
observes at runtime. Use Plumbline free, forever; reach for AgentGuard when you
need the runtime and governance story.

## Contributing

Plumbline is built to be extended. One rule = one detector module + a
vulnerable fixture + a clean fixture. See [CONTRIBUTING.md](CONTRIBUTING.md) and
[`docs/rule-authoring.md`](docs/rule-authoring.md). The full rule taxonomy is
published as a roadmap — pick an unclaimed rule and open a PR.

## License

Apache-2.0 © ActaClad Technologies. *The craft of intelligence.*
