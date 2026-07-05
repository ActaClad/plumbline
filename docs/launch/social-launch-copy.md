# DRAFT — Show HN + X thread (uncommitted)

> **Status: DRAFT — not yet published.** The remaining P2 launch copy, reusing the blog
> post's framing. Same facts, same honesty bar. Swap in the real repo URL/handle
> before posting. HN: post Tue–Thu, US morning; be in the comments all day.
> Scan numbers (`3 findings`, `93/100`) were re-verified against the shipped
> 32-rule build on `simonw/llm @ 0d593ea` (2026-07-05) — unchanged. Re-verify
> before posting only if you're on a newer Plumbline release.

---

## Show HN

### Title (pick one — ≤ 80 chars, no hype, problem-first)

1. `Show HN: Plumbline – a static analyzer for the reliability of LLM/agent code`
2. `Show HN: Plumbline – catch why your agent falls over in prod, before it ships`
3. `Show HN: Plumbline – a reliability linter for agentic code, not another scanner`

> Recommended: **#1.** Plain, says exactly what it is, no verb-y hype. #2 is
> punchier but reads slightly markety for HN. #3 picks the "not a scanner" fight
> in the title — good if you want the comment section to be about positioning.

### First comment (post immediately, from the maker)

```
Hi HN. I'm building Plumbline, an open-source static analyzer for LLM/agentic
Python.

Every AI-code scanner I could find asks "is this dangerous?" — prompt injection,
the OWASP LLM Top 10. But in my experience most agentic systems don't break
because they were attacked. They break because they were engineered badly: an
LLM call with no timeout, no retry on a 429, json.loads() on raw model output
that dies on the first markdown-fenced response, an agent loop with no iteration
cap. Nobody was statically checking for *that*. So Plumbline asks a different
question: "will this fall over in production?"

It's deterministic — AST + taint/dataflow, no LLM in the detection path, no
network, no telemetry. Same code in, same findings out, byte for byte. (There's
an optional LLM step that only rewrites the human-readable fix text; off by
default, never decides whether a finding exists.) Output is SARIF 2.1.0 (drops
into the GitHub Security tab), JSON, HTML, and a pass/fail gate for CI.

A cold scan of simonw/llm (a well-built tool) gives 3 findings, Readiness 93/100
— two are json.loads() on model output with no error handling, which is a real
crash-in-prod bug, and is exactly the kind of thing the security scanners walk
past.

Honest about where it is: 32 rules today (12 gating, 20 advisory) out of a
published ~60-rule roadmap; Python only; the taint is intra-procedural by design
(precision over recall). False positives are the thing I care most about — while
validating this release one new rule fired 9 FPs on a real response handler
(it flagged `if item.type == "function_call":`, which is structured dispatch, not
content-branching). I found it, fixed it, and added the regression test before
posting this. If you hit one, that's the most useful bug you can file.

Apache-2.0, every rule open, no held-back "pro" pack. Would love for you to point
it at your messiest agent and tell me what it gets wrong.

Repo: github.com/actaclad/plumbline
```

> HN notes: no emoji, no bold, no "🚀". Lead with the problem, not the feature
> list. The honest-limits paragraph is not optional — on HN it is the most
> credible thing you can say, and it preempts the top skeptical comment. Reply to
> every "isn't this just X?" with the specific difference, not a defense.

---

## X / Twitter thread

> 7 tweets. Tweet 1 must stand alone (it's what gets quote-tweeted). Keep each
> ≤ 280 chars (counts noted). Attach the before/after scan GIF to tweet 3.
> No thread-bait ("🧵👇" is fine once, on tweet 1).

**1/ (hook)** — ~210 chars
```
Your AI agent didn't get hacked. It fell over.

No timeout. No retry on a 429. json.loads() on raw model output that died on the
first malformed response.

Every AI scanner checks "is this dangerous?" None checked "will this fall over?"

So we built one. 🧵
```

**2/ (the gap)** — ~250 chars
```
Plumbline is a static analyzer for the RELIABILITY of LLM/agentic code.

The security scanners (OWASP LLM Top 10, prompt injection) do useful work — but
most agents break from bad engineering, not attacks. Runaway loops, no fallback,
unguarded output parsing. That's the gap.
```

**3/ (proof — attach GIF)** — ~240 chars
```
Cold scan of simonw/llm, a well-built tool, no config:

  3 findings · Readiness 93/100
  2× json.loads() on model output, no error handling → crashes on the first
  bad generation.

Real bug. Not a security issue. Which is why the scanners miss it.
```

**4/ (trust)** — ~270 chars
```
You can wire it into CI without it becoming the tool everyone mutes:

· Deterministic — AST + dataflow, no LLM in the detection path. Same code →
  same findings, byte for byte.
· No network. No telemetry. Runs fully offline.
· A rule can fail your build only with measured precision behind it.
```

**5/ (output)** — ~200 chars
```
Output is standards-grade: SARIF 2.1.0 straight into the GitHub Security tab,
plus JSON, an HTML report, and a pass/fail Quality Gate.

Findings map to OWASP / NIST / CWE where a standard exists — and where one
doesn't, that absence is the point.
```

**6/ (honest)** — ~270 chars
```
Where it honestly is: 32 rules today (12 gating) of a ~60-rule roadmap, Python
only.

While validating this release, one rule threw 9 false positives on real code. We
found it, fixed it, shipped the regression test before this thread. That loop is
the whole product — and it's public.
```

**7/ (CTA)** — ~180 chars
```
Apache-2.0. Every rule open, no "pro" pack.

  pip install actaclad-plumbline
  plumb scan ./your-agent

Point it at your messiest agent and tell us what it gets wrong.

github.com/actaclad/plumbline
```

> Strip the char-count annotations before posting. The "didn't get hacked /
> fell over" line is the same hook as the blog and demo — keep it identical
> across all three for a coherent launch.

---

## LinkedIn

> Do NOT cross-post the HN comment here — different audience, different format.
> HN rewards a dense plain-text wall and honesty; LinkedIn rewards a hook before
> the "…see more" fold (~2–3 lines), short skimmable lines, and a little
> narrative. **Put the repo link in the FIRST COMMENT, not the post** — LinkedIn
> suppresses reach on posts with external links in the body. ~200 words.

```
Your AI agent didn't get hacked. It fell over.

No timeout. No retry when the provider 429s. A json.loads() on raw model output
that crashed on the first response wrapped in a markdown fence.

I kept seeing teams ship agents that passed every security check and still broke
in production — because the failures weren't attacks. They were engineering
defects no tool was looking for.

So we built Plumbline: an open-source static analyzer that asks a different
question than the security scanners. Not "is this code dangerous?" but "will this
system fall over in production?"

It's deterministic — no LLM in the detection path, no network, no telemetry — and
it drops into CI with a pass/fail gate and SARIF straight into the GitHub
Security tab.

A cold scan of a well-built OSS tool: 3 findings, 93/100, two of them real
crash-in-prod bugs the security scanners walk right past.

It's early and I'll say so: 32 rules today of a ~60-rule roadmap, Python only. One
rule even threw false positives on real code during validation — we found it,
fixed it, shipped the test before launch. That loop is the whole point.

Apache-2.0. Point it at your messiest agent and tell me what it gets wrong.
Link in the comments. 👇

#LLM #AIengineering #AgenticAI #reliability #opensource
```

> Notes: first 2 lines carry the whole post above the fold — they must work
> alone. Kept exactly one emoji (the comment pointer); the engineer-credibility
> brand wants near-zero. The honest-limits line stays — on LinkedIn it reads as
> confidence, and it's true. First comment = `github.com/actaclad/plumbline`
> plus one line ("Repo + the honest real-repo validation writeup here:").
> A LinkedIn-native variant of the demo GIF (square/4:5, captioned — most people
> watch muted) outperforms a link to a video.

### LinkedIn first comment (post it yourself, immediately after publishing)

> Pick one. Keep it to a line or two — its job is just to carry the link the body
> can't. Drop it in the comments within a minute of posting.

1. `Repo + the honest real-repo validation writeup (every finding triaged by hand): github.com/actaclad/plumbline`
2. `Here it is — Apache-2.0, every rule open: github.com/actaclad/plumbline. The false-positive we caught and fixed pre-launch is written up in benchmark/real-repos.md.`
3. `github.com/actaclad/plumbline — `pip install actaclad-plumbline` and point it at your messiest agent. FP reports are the most useful issue you can file.`

> Recommended: **#1** — it rewards the click with the credibility artifact, not a
> sales page.

---

## Reply snippets — the "how is this different from <X>?" question

> This question hits EVERY channel within the first few replies. Answer with the
> specific difference, never a defense. Short, concrete, no link-dropping unless
> asked. Tone: plain for HN, same content slightly warmer for LinkedIn/X.

**"Isn't this just another AI scanner — agentic-radar / Agent Audit / semgrep rules?"**
```
Different question. Those map to the OWASP LLM/Agentic Top 10 — "is this code
dangerous?" Plumbline asks "will this fall over in production?": no timeout, no
retry/fallback, unguarded output parsing, runaway loops, deprecated model ids.
Reliability and architecture defects, not threats. Security is one of four
pillars here, and deliberately the smallest.
```

**"Isn't this just a linter? ruff/pylint already exist."**
```
ruff checks style and Python correctness. It has no idea what an LLM call is.
Plumbline has a framework-aware semantic layer (OpenAI/Anthropic SDK, LangChain,
CrewAI, LiteLLM) and a taint/dataflow engine, so it reasons about model calls,
tool definitions, and agent loops — e.g. "this json.loads() is parsing raw model
output with no guard," which no general linter can see.
```

**"Why not just write tests / use an eval suite?"**
```
You should — and Plumbline flags when you haven't (that's a rule). But evals tell
you the output regressed; they won't tell you a call has no timeout, or a retried
block double-charges a card, or the model id is sunset next month. It's static,
pre-runtime, and needs zero test infrastructure to find those.
```

**"It uses an LLM — how is that deterministic / how do I trust it in CI?"**
```
The detection path has no LLM, no network, no clock, no randomness — pure AST +
dataflow. Same code in, byte-identical findings out. There's an optional LLM step
that only rewrites the human-readable fix text; it's off by default and never
decides whether a finding exists. You can run the whole thing air-gapped.
```

**"What's the false-positive rate? Static analyzers are noisy."**
```
Agreed — a noisy analyzer gets uninstalled, so it's the thing we optimize hardest
against. Only High-confidence rules can fail a build, and a rule ships High only
with a measured precision number behind it; everything else is advisory. When the
analyzer can't prove a defect, it stays silent. We triage every finding on real
repos by hand and fix the FP *class* — that log is public in the repo.
```

**"Python only? What about my TypeScript/Go agent?"**
```
Python only today — that's a real limit, not a soft launch. The adapter contract
is built so other languages are additive, but we're not going wide until the
Python core has proven its precision. Honest answer: if your agent isn't Python,
it's on the roadmap, not in the box yet.
```

**"Is this just a funnel for your paid product?"**
```
Fair to ask. Plumbline is Apache-2.0 — every rule, the full catalog, no held-back
"pro" pack, and it has to be genuinely the best reliability analyzer standalone
or it fails on its own terms. We do build a runtime platform (AgentGuard) that
the static findings feed into, but the linter isn't crippled to sell it.
```

**"Show me a finding that isn't obvious / how do I know it's real?"**
```
Cold scan of simonw/llm (a well-built tool), no config: 2× json.loads() on model
function-call output with no error handling — crashes on the first malformed
generation. Hand-verified true positives, with a taint witness from the response
to the parse. The full triage (TP/FP per finding) is in benchmark/real-repos.md.
```

> If someone reports a real false positive in the thread: thank them, ask for the
> snippet, and say it'll become a fix + regression test — in public. Doing that
> visibly, on launch day, is worth more than any feature claim.
