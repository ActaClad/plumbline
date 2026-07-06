# Plumbline OSS launch — plan & playbook

> **Status: internal working doc.** Sequencing, channel playbook, LinkedIn
> personal-vs-company split, Reddit call, and the 4-page carousel spec. Pairs with
> the copy in `launch-blog-post.md`, `social-launch-copy.md`, and `demo-script.md`.

## Where this fits

The **ActaClad company launch** already ran on LinkedIn (2026-07-01→02: "We're
Live", the 3-slide brand carousel, ~100 reactions). This is a **separate event —
the Plumbline *OSS* launch** — for a developer audience. It leads with the *tool*
and the reliability wedge, not the company. Do **not** re-run the company launch
copy; this is the follow-on the company post promised ("more about Plumbline over
the coming weeks").

**Readiness:** package live on PyPI, repo public, release v0.0.1 published, CI
green, README/FAQ/install-note done. Effectively launch-ready. **One true blocker:
the demo GIF** — record it with `vhs docs/launch/demo.tape` (see checklist).

## The one rule: don't fire every channel at once

**Hacker News is the anchor, and Show HN *demands you're in the comments all day*.**
You cannot be present everywhere simultaneously. So everything sequences off the
HN day — pick it, clear your calendar for it, and stagger the rest around it.
Simultaneous blasting = thin presence everywhere and a dead HN thread.

## The sequence

Anchor = **HN day**. Recommend **Tue 2026-07-07 or Wed 2026-07-08, ~08:30 US
Eastern** (Show HN rewards Tue–Thu US morning; avoid Fri/weekend).

| When | Channel | Action |
|---|---|---|
| **T-0, 08:30 ET** | **Hacker News** | Show HN (title #1). Paste the maker first-comment immediately. Then live in the thread **all day**. |
| T-0, +30–60 min | **X/Twitter** | The 7-tweet thread. Tweet 1 stands alone; **attach the GIF to tweet 3.** |
| T-0, same morning | **LinkedIn** | Durai **personal** post + carousel; ActaClad **page** reshares within the hour. Repo link in the **first comment**, not the body. |
| T-0, daytime | **Blog** | Publish `launch-blog-post.md` (dev.to / Hashnode for SEO); embed the GIF; link from HN/X if asked. |
| **T+1** | **Reddit** | Tailored posts (below) — *after* you know the HN reaction and can reference it. |
| T+2 … T+7 | Follow-ups | The pre-launch FP catch, the Gemini-adapter dogfood story, a rule deep-dive. Sustains the launch past day one. |

## Accounts & posting identity

We have **no HN / X / Reddit presence yet** and a strong **personal LinkedIn**
(the July-1 founder post pulled ~100 reactions). Who you post *as* differs by
platform — and on some, a company account actively backfires. The rule of thumb:
**HN and Reddit reward a real person who built the thing; a company account
announcing itself is an anti-pattern there. X and LinkedIn-page are fine as the
brand.**

| Platform | Post as | Why |
|---|---|---|
| **Hacker News** | **Personal (the maker)** — never a company account | No "company page" exists on HN; a brand account posting Show HN reads as marketing and gets flagged. HN ranks by **upvotes, not followers**, so having no audience doesn't hurt — **this is the best channel for us.** |
| **X / Twitter** | **Company (@actaclad) is fine** (worth owning long-term) | Company accounts are normal on X. But a **zero-follower account gets ~no organic reach** day one — the thread is an artifact to embed/link from HN + LinkedIn and a seed for later, not a launch driver. |
| **Reddit** | **Personal with some karma** — not a brand/new account | Reddit filters corporate + low-karma/new accounts hard (auto-removal, self-promo rules). A fresh "actaclad" account will likely be removed. Defer Reddit, or use a personal account and genuinely participate first. |
| **LinkedIn** | **Personal drives; company page is of-record** (see below) | Personal reach ≫ company-page reach on LinkedIn. |

**Warm the accounts first.** Create the HN (and Reddit, if used) accounts a few
days before launch and leave one or two genuine comments — a zero-history account
posting on day one trips spam filters. Set expectations: with no following on
HN/X/Reddit, **HN is the equalizer** (merit-ranked); treat X/Reddit as secondary.

**Growing the ActaClad LinkedIn page — the counter-intuitive part.** The goal
(more page followers) is right, but **launching *from* the company page is the
wrong mechanism** — LinkedIn throttles company-page reach to a fraction of
personal. The split that actually grows the page:

1. **Post natively from the personal profile** (the reach driver — write a post,
   not a reshare).
2. **@-mention/tag the ActaClad page** in it + a plain *"Follow ActaClad for
   more."* — the tag is what converts profile clicks into follows.
3. **Also post from the company page** (announcement + carousel, of-record) and
   **reshare it from personal within the hour.**
4. **Repo link in the first comment**, not the body.

Personal drives reach and funnels follows to the page via the tag + CTA; the page
is the destination and archive, not the megaphone.

## Channel playbook

### Hacker News — the anchor
- **Title #1** ("Show HN: Plumbline – a static analyzer for the reliability of
  LLM/agent code"). Plain, problem-first.
- Paste the drafted maker first-comment the moment it's live.
- **Be in the comments all day.** Reply to every "isn't this just \<X\>?" with the
  *specific* difference (reply snippets are drafted). Thank FP reporters and turn
  their snippet into a public issue **during the thread** — doing that visibly on
  launch day is worth more than any feature claim.

### X / Twitter
- The 7-tweet thread is drafted; strip the char-count annotations. GIF on tweet 3.
- Post within the hour of HN so a good HN run and the thread amplify each other.

### LinkedIn — personal drives, company is of-record
LinkedIn suppresses reach on posts with external links in the body, and a
*personal* founder post consistently out-reaches a company page. So:

- **Durai (personal page) — the driver.** Post the drafted Plumbline LinkedIn
  copy (narrative + honest limits + the ask). This is *new* copy, **not** a repeat
  of your July-1 company launch. Attach the **4-page carousel** (spec below).
  **Put `github.com/ActaClad/plumbline` in the first comment**, plus one line
  ("Repo + the honest real-repo validation writeup").
- **ActaClad (company page) — of-record + asset host.** A crisp product
  announcement with the same carousel; **reshare Durai's post** within the hour.
- Do **not** cross-post the dense HN maker-comment here — wrong format for the
  audience.

### Reddit — qualified yes, secondary, T+1
Real value, but **each sub has strict self-promo rules and an identical
cross-post gets removed/downvoted.** Tailor per sub; never let it compete with
HN-day presence.
- **r/LocalLLaMA** — dev-heavy, receptive to agent tooling. Lead with the
  reliability gap and the deterministic/offline angle.
- **r/mlops** — the CI-gate / SARIF / "reliability regression can't merge" framing
  lands squarely.
- **r/Python** — use the **weekly "Showcase"/"What are you working on" thread**;
  read the sidebar self-promo rules first.
- Optional: **r/devops**, **r/artificial** (lower signal).
- Each post: tailored intro, repo link, be present for comments. Verify each sub's
  current rules the day you post — they change.

## The 4-page LinkedIn carousel — spec

**Deliverable note:** a rendered HTML mockup of all four slides lives at
`docs/launch/carousel-mockup.html` (open it, or the published artifact). Below is
the copy/visual brief; **final designed PNGs are rebuilt in Canva** from it.

**Brand system** (from the company launch carousel — match it exactly):
- Background near-black `#0D0D0D`; accent gold/amber `#C8951E`; text cream
  `#EDE6D6`; subtle dark-brown geometric "AC" hex motif; the white rounded
  connector-line-with-dots motif.
- Bold **display serif** for headlines; rounded **sans** for body/labels.
- Format **1080×1350 (4:5)** for maximum feed height.
- The Plumbline `</>` mark on slide 1; "ACTACLAD.COM" footer on each.

**Locked at 4 slides** (keeps both the outcomes checklist *and* the proof):

| # | Headline | Body / visual |
|---|---|---|
| **1 — Hook + category** | **"Your AI agent didn't get hacked. It fell over."** | Sub (the canonical line): *"Security scanners tell you if your AI can be attacked. Plumbline tells you if it can survive production."* Then *"Introducing Plumbline — open-source static analyzer for LLM & agentic apps."* |
| **2 — What it checks** | **"These aren't security bugs. They're production bugs."** | Outcomes checklist (✓): infinite loops · missing retries & timeouts · unguarded output parsing · uncapped token cost · deprecated/misconfigured models · no eval/tracing · Readiness score + fixes · skill-pack export for your coding agent. Stat bar: **60-rule catalog · 32 available today · Apache-2.0 · 100% open**. |
| **3 — Proof** | **"3 findings. 93/100. On a well-built tool."** | The real branded HTML report card (score + pillar bars + gate). Caption: *"Caught here: unguarded output parsing, no tracing. Deterministic · no LLM in detection · offline."* |
| **4 — CTA** | **"Ready in under 30 seconds."** | `pip install actaclad-plumbline` → `cd your-agent && plumb scan --open` → `plumb export-skills`. ✔ HTML report ✔ Readiness score ✔ Suggested fixes ✔ Zero config. *"Point it at your messiest AI project. Tell us what we missed."* `github.com/ActaClad/plumbline` (also in first comment). |

Keep emoji at ~zero (engineer-credibility brand). **The slide-1 hook + canonical
category line are identical across the blog / HN / X / both LinkedIn posts** —
never a paraphrase. **Stats stay honest:** "60-rule catalog · 32 today," never
"60 reliability rules."

## Pre-launch checklist

- [ ] **Record the demo GIF** — `vhs docs/launch/demo.tape` → attach to blog + X
  tweet 3 + carousel slide 3. *(the only blocker)*
- [ ] **Design the 4-page carousel** from the spec above (Canva, brand palette).
- [ ] **Final copy pass** — pick HN title (#1), strip char-count annotations from
  the X thread, confirm repo URL case (`ActaClad/plumbline`).
- [ ] **Publish the blog** (dev.to/Hashnode), embed the GIF, swap real links.
- [ ] **Create + warm the accounts** a few days early — personal HN account
  (and Reddit, if used); the ActaClad X handle. Leave 1–2 genuine comments so
  they're not zero-history on launch day. (See *Accounts & posting identity*.)
- [ ] **Clear the HN day** — you must be in the thread all day.
- [ ] **Website analytics** — enable Vercel Web Analytics / add GA4 so launch-day
  UTM traffic from these posts is actually measured (company TODO).
- [x] Package on PyPI; pip / pipx / uv install paths work
- [x] Release v0.0.1 published; trusted-publishing pipeline proven; CI green
- [x] README: TL;DR, badges, install note, FAQ, skills-export elevated
- [x] Issue templates (incl. FP report), CONTRIBUTING, real-repo validation writeup

## After launch (sustain)

Have 2–3 follow-ups queued so the launch isn't a single spike:
- **"We caught a false positive in our own tool before launch"** — the OUT-002
  envelope-field FP, fixed with a regression test pre-publication.
- **"A real Gemini app was invisible, so we shipped an adapter in a day"** — the
  voice-agent recall-gap → `adapters/gemini.py` story (dogfooding the FP/recall
  loop the launch promises). Strong "we point it at real code" proof.
- A rule deep-dive (e.g. why `json.loads` on model output is the most common
  crash-in-prod defect).
