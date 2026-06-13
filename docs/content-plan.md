# Thought-Leadership Content Plan

Content is not marketing *alongside* Plumbline — it is the same flywheel:
**OSS tool earns developer trust → content compounds reach and positions
ActaClad as the authority on agentic engineering quality → that authority makes
AgentGuard the obvious paid choice → consulting engagements feed new production
scars back into rules and content.**

## The one thesis everything ladders up to

> *AI-assisted coding means more agent code, written faster, reviewed less — and
> most of it fails on reliability and architecture, not security. Here is what
> good agentic engineering looks like.*

Every piece is a facet of this. It is also the positioning that keeps Plumbline
out of the crowded "security scanner" conversation.

## Three tiers

### Tier 1 — Rule explainers (the engine; ~weekly)
Each rule is a post: the production failure that motivates it → the bad code →
the fix → why static analysis catches it. ~40 rules = ~a year of content that
doubles as documentation and SEO. **The rule catalog IS the editorial calendar.**
Low effort per post; high cumulative compounding. Start with the High-confidence
Reliability rules — they're the most visceral ("your agent loop never
terminated and burned $4k overnight").

### Tier 2 — Synthesis / authority pieces (monthly)
The pieces that build authority, not just traffic. Seed list:
- "Linters are dying. Static analysis is exploding. Here's the difference." (the
  agentic-coding argument — concedes style-linting is fading, shows why semantic
  analysis is *more* needed.)
- "The reliability defects hiding in AI-generated agent code." (anonymized
  consulting scars: no fallback, no self-critique, silent model drift.)
- "What good agentic engineering looks like." (the manifesto — the piece people
  cite; effectively the public face of the rule catalog's worldview.)
- "Design-time vs runtime: why agent quality needs both." (the Plumbline +
  AgentGuard worldview, told as engineering, not sales.)
- "Why we made our analyzer deterministic when everyone's reaching for LLM
  judges." (the neuro-symbolic argument; technical credibility.)

### Tier 3 — Build-in-public (continuous, near-zero marginal cost)
Because you build agentically and capture decisions as ADRs, **the ADRs are
content.** "How we built a taint engine for agent code." "Why detection is
deterministic and only remediation uses AI." Developers love watching real
engineering decisions. You're producing the artifacts anyway — repackage them.

## Cadence and distribution

- **Cadence:** weekly Tier-1, monthly Tier-2, opportunistic Tier-3. Consistency
  beats volume.
- **Channels:** pick TWO and own them. For a developer-credibility play: a
  technical blog on the docs/OSS site (SEO + permanence) + one social channel
  where your buyers actually are. Do not spray five channels.
- **Format discipline:** every Tier-1 post ends with a runnable `plumb` example.
  Every Tier-2 post links to the manifesto and the repo. Every post is
  engineer-to-engineer, no fluff.

## Sequencing vs. the build

- Don't publish Tier-1 rule posts before that rule actually ships — credibility
  dies if `plumb` doesn't do what the post says.
- Publish the manifesto (Tier-2) around the time the Reliability core (M3) is
  usable — that's when you can say "and here's the tool that checks it."
- Build-in-public (Tier-3) can start immediately — the ADRs already exist.

## Measurement

Vanity metrics are a trap. Track: GitHub stars/contributors (community health),
PyPI installs (adoption), and — the one that matters — **inbound AgentGuard
demo requests that mention Plumbline** (the flywheel actually turning).
