# Plumbline — Open-Source Distribution & Community Strategy

> The complete playbook for taking Plumbline public: how to build adoption, a
> contributor community, and credibility that earns clients for AgentGuard and
> ActaClad — without poisoning the open-source goodwill that makes it work.
>
> Companion: [`launch-checklist.md`](launch-checklist.md) — the same content as a
> priority-ordered, knock-it-out checklist.

---

## 0. The mental model (internalize before anything else)

Four truths that prevent the mistakes first-time OSS maintainers make.

1. **Stars are a vanity metric; adoption and retention are real.** A repo with
   2,000 stars and nobody running it in CI is worthless; 200 stars where 50 teams
   gate every PR on it is a business. Optimize for *"a developer ran `plumb scan`,
   got real value in 5 minutes, and wired it into CI."* Stars are a lagging
   byproduct of that, never the goal.

2. **Launch is a moment; community is a practice.** The Hacker News spike fades in
   48 hours. What compounds is the boring discipline: replying to issues within a
   day, merging good PRs fast, keeping docs current. **The first 90 days of
   responsiveness set the project's culture permanently.** A repo that *feels*
   alive pulls contributors; stale PRs and unanswered issues repel them more than
   any missing feature.

3. **The commercial funnel must be earned, never extracted.** The fastest way to
   poison OSS goodwill is to make the free tool feel like crippleware for
   AgentGuard. `CLAUDE.md` already states this ("never feel like crippleware… the
   funnel is earned by being good"). Hold that line religiously — the credibility
   *is* the funnel.

4. **Distribution = meeting developers inside their existing workflow,** not "it's
   on PyPI." A scanner devs must remember to run manually is a scanner they forget.
   The win is `pre-commit`, a GitHub Action, and a CI one-liner — it runs itself.

**The overriding pre-condition: precision before publicity.** A dev tool that
emits false positives gets uninstalled and trashed in the launch-day comments —
and you get one launch. Finish the real-repo dogfooding and fix the FP classes
*before* going wide. This is the highest-priority item on the entire list.

---

## 1. Pre-launch repo readiness

Plumbline is already ahead of most pre-launch projects (README, CONTRIBUTING,
ADRs, CI, benchmark, license, changelog). Gaps to close before going public:

**Community-health files** (GitHub surfaces and scores these):
- `CODE_OF_CONDUCT.md` — Contributor Covenant (standard, copy-paste).
- `SECURITY.md` — private vulnerability reporting process. A *security-adjacent
  tool* with no security policy is a bad look. Enable GitHub private vuln
  reporting.
- `.github/ISSUE_TEMPLATE/` — `bug_report`, `rule_request`, and crucially a
  **`false_positive_report`** template (command, input snippet, expected vs
  actual, version). For a linter, FP reports are your most important signal —
  route them deliberately.
- `.github/PULL_REQUEST_TEMPLATE.md` — checklist tied to your invariants (one
  detector + bad fixture + good fixture + test; ADR if a decision is made).
- `CODEOWNERS`, `.github/FUNDING.yml`, and a labeled issue taxonomy
  (`good first issue`, `help wanted`, `false-positive`, `new-rule`, `precision`,
  `adapter`, `docs`).

**Repo polish:**
- A real **social preview image** (Settings → Social preview) — what renders when
  the link is shared on X/Slack/HN.
- Crisp **About** sidebar + **topics**: `static-analysis`, `llm`, `agents`,
  `ai-safety`, `reliability`, `python`, `sarif`, `linter`, `langchain`, `crewai`.
- **Pin** the 2–3 issues you want first contributors on; enable **Discussions**
  (Q&A, Show-and-tell, Ideas); cut a first **GitHub Release** from `CHANGELOG.md`.
- A **one-command dev setup** (dev container or `make dev`) so a contributor goes
  from clone to green tests in minutes — contribution friction kills PRs.

**Do not publicize until:** real-repo precision is solid, the README's 5-minute
promise is literally true (verified), and a fresh-machine `pip install` works
(wheel verified).

---

## 2. Legal, licensing & IP

- **License — Apache-2.0 (chosen) is correct.** Its explicit patent grant (which
  MIT lacks) is what enterprise legal teams want; keep it for a tool meant for
  corporate adoption.
- **Contributor agreement — decide before PR #1:**
  - **DCO (Developer Certificate of Origin)** — `Signed-off-by` on commits.
    Lightweight, no friction, the modern norm (Linux, GitLab). **Recommended** —
    lowest barrier, which matters when you want contributors.
  - **CLA** — lets the company relicense; more friction, some contributors refuse
    on principle. Only if AgentGuard licensing genuinely needs it — for a
    permissive catalog it usually doesn't.
- **Trademark — the under-appreciated one for company-backed OSS.** The code is
  Apache-2.0, but **"Plumbline", "ActaClad", "AgentGuard" should be marks you
  control.** Anyone may fork the code; no one may ship a competing *"Plumbline."*
  This keeps the brand as the funnel even though the code is free. Add a
  `TRADEMARK.md` and file the marks when budget allows.
- **Squat your names today:** PyPI (`actaclad-plumbline`), a GitHub **org** named
  `actaclad` (not a personal account — orgs signal legitimacy and continuity), the
  domain, npm (future JS port), X handle, Discord vanity. Post-launch collisions
  are painful.
- **Publish the open-core boundary.** State plainly: forever-free = the engine,
  all rules, the catalog; AgentGuard adds runtime, traces, governance. Ambiguity
  scares both contributors (rug-pull fear) and customers. Clarity is trust.
- **Supply-chain hygiene** (credibility for a security-adjacent tool): pinned
  deps, Dependabot, signed releases / PyPI trusted publishing (OIDC, no tokens),
  an SBOM, and eventually an **OpenSSF Best Practices badge** / Scorecard.

---

## 3. The distribution surface (make it run itself)

Ranked by leverage for a CI-oriented dev tool:

1. **PyPI** — `pip install actaclad-plumbline`. Automate publish on tag via GitHub
   Actions trusted publishing (OIDC).
2. **GitHub Action** (`actaclad/plumbline-action`) — *the* highest-leverage
   artifact. Teams adopt a scanner the day it's a 5-line `uses:` block that uploads
   SARIF to the Security tab. **Ship with launch, not later.**
3. **`pre-commit` hook** — publish `.pre-commit-hooks.yaml`; catches defects at
   commit time and gets you ecosystem discoverability.
4. **SARIF → GitHub code scanning** (already emitted) — lean in hard; "findings
   appear in your Security tab" is a concrete, demoable hook.
5. **Docker image** — for non-Python CI and env-averse users.
6. **Later:** Homebrew tap, a **VS Code extension** (consumes your SARIF —
   design-time feedback in the editor is sticky), `uvx plumbline`.

Each artifact is also a content piece ("Gate your LangChain app's reliability in
CI in 5 minutes").

---

## 4. The launch (a sequenced campaign, not a button)

**Pre-stage (quiet):** soft-launch to 10–20 friendly agentic-AI developers; watch
them run it cold on *their own* repos. This catches the FPs and onboarding
friction the launch crowd will roast you for. Worth more than any launch copy.

**Channels, in order of fit:**
- **Show HN** — "a reliability/architecture linter for LLM & agent code." HN loves
  the contrarian angle ("everyone builds security scanners; reliability is the
  uncovered gap"). Post Tue–Thu US morning, be in the comments **all day**
  (engagement drives ranking), lead with the problem, and be **radically honest
  about limitations** (HN rewards candor, punishes hype).
- **Reddit:** r/LLMDevs, r/LocalLLaMA, r/MachineLearning (strict), r/Python. Frame
  as "I built X to solve Y."
- **X/Twitter AI-engineering crowd** — the "agents fall over in production"
  narrative is hot; a thread with a real before/after scan travels.
- **Framework Discords** (LangChain, LlamaIndex, CrewAI) + AI-eng communities — be
  useful, not spammy.
- **Product Hunt** — secondary spike; lower fit for a CLI.
- **dev.to / Hashnode** cross-posts for SEO long-tail.

**Assets ready before launch:** a 60–90s terminal demo (asciinema GIF/video), the
launch blog post, a real before/after scan on a recognizable repo, and the GitHub
Action snippet. The demo doing real work on real code is your strongest asset.

---

## 5. Content & credibility (moat-building)

Everything leads with the **reliability/architecture wedge** — never "another
security scanner," or you blur into the crowd.

- **The rule catalog as a public, browsable site** (GitHub Pages / MkDocs /
  Docusaurus). Your docs call it the de-facto reference for "what good agentic
  engineering looks like." It is simultaneously SEO (people search "agent loop
  without max iterations"), a credibility artifact, and your contribution surface
  (each "help wanted" rule links a good-first-issue).
- **Honest comparison content:** "Plumbline vs agentic-radar / Agent Audit —
  reliability vs security." Owning the comparison page owns the framing.
- **Standards coverage matrix** (OWASP LLM/Agentic, NIST AI RMF, CWE) — enterprise
  credibility; publish it.
- **Publish the benchmark AND the real-repo validation honestly** — including "we
  found false positives on babyagi and fixed them." Counterintuitive truth: in dev
  tools, **transparent honesty about limitations builds more trust than claimed
  perfection.** A measured-precision-plus-known-weaknesses page out-credentials any
  "100% accurate!" claim.
- **The "you are flying blind" narrative** (EVAL-001/OBS-001) — your strongest
  emotional hook and the natural AgentGuard bridge: make a team *feel* the risk,
  then show the static proof.
- **Get listed** in awesome-lists (awesome-llmops, awesome-ai-agents,
  awesome-static-analysis) and, over time, in framework docs and CI marketplaces —
  integrations are distribution.

---

## 6. Community & the contributor funnel

Your flywheel is the **"add a rule in an afternoon"** promise — make it real:
- A `good first issue` per high-value roadmap rule, each linking the rule-authoring
  guide and an existing rule to copy. Contributors who ship a rule become
  evangelists.
- **Recognize everyone** — all-contributors bot, release-note shout-outs, a
  `MAINTAINERS.md` path. People contribute for impact *and* recognition.
- **Triage discipline:** label fast, respond within ~24h (even "thanks, looking"),
  close stale items kindly. A visibly-present maintainer is the #1 contributor
  magnet.
- **A lightweight `GOVERNANCE.md`** ("ActaClad maintains; review criteria are X")
  + a **public `ROADMAP.md` / Projects board** — reassures people their PRs won't
  vanish and the project won't rug-pull, and recruits contributors to specific
  items.
- **Counter company-OSS skepticism** (communities are wary of company-controlled
  projects) with transparency, governance, and a no-rug-pull track record.
- **Community space:** start with GitHub Discussions (zero overhead). Add Discord
  only when volume can keep it from looking empty — an empty Discord is worse than
  none.
- **Personally recruit and celebrate the first ~10 contributors;** that cohort
  sets the tone and gives you your first evangelists.

---

## 7. The commercial funnel (OSS → AgentGuard, done right)

- **A gentle pointer, never a nag.** In docs and the flying-blind findings, a
  single line: *"Plumbline flags the design-time risk; AgentGuard confirms it at
  runtime — [learn more]."* No upsell modals, no feature-gating, no
  register-to-scan.
- **Telemetry — handle with extreme care; this can detonate trust.** Any usage
  analytics must be **opt-in, transparent, documented, trivially disabled**, and
  must **never** phone home from the detection path (network in detection is
  already forbidden — keep it sacred). When unsure, collect nothing. Many devs
  judge the whole project on whether the CLI quietly calls home.
- **Open-core line:** free = the whole analyzer + catalog forever; paid =
  AgentGuard runtime/traces/governance. **Never** move a previously-free rule
  behind a paywall — that earns a front-page "they rug-pulled it" thread.
- **The real conversion path** is not "OSS user clicks buy." It's: a team adopts
  Plumbline → it becomes part of how they ship → they hit the runtime/governance
  wall it points at → ActaClad arrives with *earned trust*. OSS buys trust and
  distribution; the sale is a separate, warmer motion.
- **Attribution plumbing:** UTM the docs→AgentGuard links and use
  privacy-respecting analytics (e.g. Plausible) so you can prove the OSS→pipeline
  contribution internally.

---

## 8. Metrics that matter (vs vanity)

- **Real:** PyPI downloads + install→retention, CI/Action integrations, unique
  repos scanned, issue/PR velocity, **false-positive-report trend** (your top
  quality signal), contributor count, time-to-first-response.
- **Vanity-but-signal:** star *velocity* (not absolute), HN/Reddit reach.
- **Business:** AgentGuard demo requests attributed to Plumbline (the number that
  justifies the OSS investment internally).
- Instrument the docs and links, not the tool.

---

## 9. Versioning, stability & release strategy

A tool teams gate CI on must be *predictable*:
- **SemVer.** Stay `0.x` until the rule/Finding contract is stable; `1.0` signals
  "safe to depend on" — don't rush it, but do reach it.
- **Rule-stability policy, stated publicly:** new rules ship **advisory (Medium)
  first and gate (High) only after measured precision** — so an upgrade never
  surprise-breaks someone's CI. (You already do this; document it as a promise.)
- **Predictable cadence** — regular small releases signal life; long silence reads
  as dead. Automate release + changelog.
- **Baselines** (already built) let teams adopt on a dirty repo and gate only new
  findings — lead with this in onboarding; it removes the #1 adoption objection.

---

## 10. Onboarding & time-to-value

- The **5-minute promise** is sacred: `pip install` → `plumb scan ./app` → useful
  output. Protect it in every release.
- Sensible zero-config defaults; consider `plumb init` to scaffold config + CI.
- A killer **quickstart** and the demo GIF above the fold in the README.

---

## 11. Risk & crisis handling

- **The #1 killer is maintainer neglect,** not missing features. A 3-month-quiet
  repo reads as dead. Budget *sustained* maintainer time before launching — a big
  launch you can't sustain is worse than a slow build.
- **The FP-firehose trap:** ship noisy → get uninstalled → never recover.
  Precision discipline is the brand.
- **Scope-creep-for-stars trap:** resist "add JavaScript!", "100 more rules!"
  requests that dilute the wedge. *A linter right 40 times beats one noisy 200.*
- **Have a plan** for a real security bug in Plumbline (responsible disclosure via
  `SECURITY.md`) and for a viral negative thread (respond fast, honestly, fix in
  public).

---

## 12. Sequenced plan (high level — see the checklist for the granular version)

1. **Now → launch-ready (the gate):** finish real-repo dogfooding (10–15 repos),
   fix/triage FP classes, close community-health gaps, move to an `actaclad` org,
   claim all names, ship the **GitHub Action + pre-commit**, build the demo + blog.
   *Do not launch until real-repo precision is solid.*
2. **Launch week:** Show HN (present all day) → Reddit → X thread → Discords. Lead
   with the reliability wedge and radical honesty.
3. **First 90 days:** respond fast, convert every FP report into a fix+test, seed
   and shepherd good-first-issue rules, publish the catalog site + 2–3 content
   pieces, land the first external contributor.
4. **Ongoing:** ship small and often, grow the catalog *with* the community, keep
   the AgentGuard pointer gentle, let credibility compound.
