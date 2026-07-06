# DRAFT — Launch blog post (uncommitted)

> **Status: DRAFT — not yet published.** The P2 launch post. Leads with the reliability
> wedge and the "flying blind" problem; carries one real before/after; is openly
> honest about limits. Engineer-to-engineer, no marketing fluff (CLAUDE.md §8).
> ~1,100 words. Swap in the real org/handle/links before publishing. Cross-post
> to dev.to/Hashnode for SEO; trim the first three sections into the Show HN text.

---

## Your AI agent didn't get hacked. It fell over.

There is a whole category of tools that scan AI code, and they all ask the same
question: *is this dangerous?* Prompt injection, insecure output handling, the
OWASP LLM Top 10. Useful work. But it is not why most agentic systems break in
production.

Most agentic systems don't break because someone attacked them. They break
because they were **engineered badly**: a model call with no timeout that hangs
the worker pool. No retry when the provider 429s. A `json.loads()` on raw model
output that crashes on the first response wrapped in a markdown fence. An agent
loop with no iteration cap that burns $400 in tokens before anyone notices. A
deprecated model id that turns into a scheduled outage on the provider's cutoff
date.

These are **reliability and architecture defects**, and no static analyzer was
looking for them. So we built one.

**Security scanners tell you if your AI can be attacked. Plumbline tells you if it
can survive production.** It's a static analyzer for the reliability of LLM and
agentic Python — it asks a different question than the security scanners: not
*"is this code dangerous?"* but *"will this system fall over in production?"* — and
it answers it at design time, before the incident, from the source alone.

## What it looks like

Here is a cold scan of [`simonw/llm`](https://github.com/simonw/llm) — a widely
used, well-engineered CLI — pinned at a real commit, with no configuration:

<!-- Re-verified against the shipped 32-rule build (plumb 0.0.1) on
simonw/llm @ 0d593ea, 2026-07-05: same 3 findings, same 93/100 — only the
loaded-rule count moved 25 -> 32. Re-verify before publishing if on a later
Plumbline release. -->

```
$ plumb scan ./llm

  Critical/High   PLB-OUT-001  llm/default_plugins/openai_models.py:1027
  Critical/High   PLB-OUT-001  llm/default_plugins/openai_models.py:1143
  Major/Medium    PLB-OBS-001  llm/default_plugins/openai_models.py:961

3 findings across 49 file(s); 32 rule(s) loaded.  gate failed
Readiness Score: 93/100 · Reliability 80  Architecture 100  Harness 99  Security 100
```

Three findings on a good codebase. Not a 200-line wall of maybes — three, with a
high score, because the tool is genuinely well-built. The two that fail the gate
are the same defect twice:

> **PLB-OUT-001 — LLM output parsed as JSON without error handling.**
> `json.loads()` is called on model-generated function-call arguments with no
> guard. Models produce malformed JSON regularly — fences, truncation, a prose
> preamble — and the first bad generation raises straight out of the request.
> *Fix:* validate against a schema and handle the parse failure, or use the
> provider's structured-output mode.

That is a real bug in a real tool. It is **not** a security issue — which is
exactly why the security scanners walk past it. That gap is the whole reason
Plumbline exists.

## How it works (and why you can trust the output)

Two commitments make Plumbline something you can wire into CI without it becoming
the tool everyone mutes:

**Detection is deterministic.** The engine is pure static analysis — an AST plus
a taint/dataflow tracker, no LLM in the detection path, no network, no telemetry.
Run it twice on the same code and you get byte-identical findings. (An LLM can
*optionally* rewrite the human-readable fix text, off by default — it never
decides whether a finding exists.) Your security team can verify this: analysis
runs fully offline.

**False positives are the enemy.** Every finding is High, Medium, or Low
confidence. Only **High** can fail a build, and a rule ships High only with a
*measured* precision number behind it. The mechanism is a tri-state resolver:
when the analyzer can't prove an attribute is absent, it stays silent rather than
guess. We would rather miss a defect than cry wolf — because a noisy analyzer
gets uninstalled, and then it catches nothing at all.

Output is standards-grade: SARIF 2.1.0 (drop it straight into the GitHub Security
tab), JSON, a self-contained HTML report, and a pass/fail **Quality Gate** for
CI. Findings map to OWASP LLM/Agentic Top 10, NIST AI RMF, and CWE where a
standard exists — and for the reliability and architecture rules, where no
standard exists, that absence *is* the point.

## What we're honest about

This is v0.1, and a reliability tool that overpromises is its own kind of
unreliable. So, plainly:

- **32 rules are implemented today** — 12 gating, 20 advisory — out of a published
  ~60-rule taxonomy. The rest is a contributor roadmap, deliberately weighted
  toward the reliability and architecture rules, not the crowded security space.
- **Python only.** The adapters cover the raw OpenAI/Anthropic SDKs, LangChain/
  LangGraph, CrewAI, and LiteLLM. Other stacks are invisible until an adapter
  exists — and we tell you when a file produced zero semantic nodes.
- **Taint is intra-procedural by design.** It misses some cross-function flows.
  That is a precision choice, not an oversight — we don't loosen it to chase
  recall.
- **We move rules to advisory when the data says so.** Our hardcoded-secret rule
  looked perfect on curated fixtures, then threw a new false-positive class on
  nearly every real repo we scanned — so we downgraded it to advisory and let
  the dedicated secret scanners own that job. While validating this release's new
  rules, one of them fired nine false positives on a real response handler
  (it flagged `if item.type == "function_call":` — structured dispatch, not
  content-branching). We found it, fixed it, and shipped the regression test
  *before* this post went out. That loop — point it at real code, triage every
  finding by hand, fix the false-positive *class* — is the work, and it is public
  in [`benchmark/real-repos.md`](../../benchmark/real-repos.md).

## Try it, and break it

```
pip install actaclad-plumbline
cd your-agent && plumb scan
```

It's Apache-2.0 and genuinely open — every rule, the full catalog, no held-back
"pro" pack. If you get a false positive, that is the single most valuable bug you
can file: it comes with a template, and we turn it into a fix plus a regression
test, in public. If you want to add a rule, one rule is one detector module plus
a vulnerable and a clean fixture — an afternoon's work, and the roadmap is full
of unclaimed ones.

Point it at your messiest agent. Tell us what it gets wrong.

→ **github.com/ActaClad/plumbline**

---

*Plumbline is built by ActaClad. It's the design-time companion to our runtime
trust platform, AgentGuard — the static linter flags the risk; the runtime
confirms the incident. But Plumbline stands entirely on its own, and always
will.*
