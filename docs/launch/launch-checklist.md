# Plumbline — Launch & Community Checklist

> Priority-ordered, knock-it-out-one-by-one. Tiers: **P0** = do not go public
> until done · **P1** = launch-ready repo · **P2** = launch execution · **P3** =
> first 90 days · **P4** = ongoing growth. Rationale for each item is in
> [`distribution-strategy.md`](distribution-strategy.md).

Legend: `[ ]` todo · `[~]` in progress · `[x]` done.

---

## P0 — Blockers (do NOT publicize until every box is checked)

- [~] **Real-repo precision pass.** Scan 10–15 real OSS agentic repos; triage every
      finding; fix or backlog each FP **class**. Precision before publicity.
      (**8 repos triaged** — babyagi, llm, crewAI, crewAI-examples, gpt-researcher,
      open-interpreter, pydantic-ai. The gating rules' FP-class curve has
      **flattened**; LiteLLM adapter added (recall). SEC-004 surfaced a new FP
      class on nearly every repo → **downgraded to advisory/non-gating**. Mostly
      there for a soft-launch; a few more scans would keep confirming. See
      `benchmark/real-repos.md`.)
- [ ] **Fresh-machine install works.** `pip install` from the built wheel on a
      clean env → `plumb scan` gives useful output. (Verified once; re-verify at
      release.)
- [ ] **README 5-minute promise is literally true** — every command shown runs and
      does what it says. (Verified; re-check after any CLI change.)
- [ ] **Claim all names** (do today, even pre-1.0): PyPI `actaclad-plumbline`,
      GitHub **org** `actaclad`, domain, X handle, Discord vanity, npm (future).
- [ ] **Move the repo into the `actaclad` GitHub org** (not a personal account) —
      legitimacy + continuity.
- [x] **Decide & document the contributor agreement** — recommend **DCO**
      (`Signed-off-by`); add a one-paragraph `CONTRIBUTING` note + a DCO check.
      (DCO chosen; CONTRIBUTING "Sign your commits" section + `.github/workflows/dco.yml`.)
- [x] **Publish the open-core boundary** — one short section (README + site):
      forever-free = engine + all rules + catalog; AgentGuard = runtime/governance.
      (README "What's free forever vs. what AgentGuard adds"; mirror on site at launch.)
- [~] **`SECURITY.md` + enable GitHub private vulnerability reporting** — a
      security-adjacent tool must have a disclosure path. (`SECURITY.md` added;
      **TODO (you): enable private vulnerability reporting in repo Settings → Security.**)
- [x] **Confirm no telemetry / no network in the detection path** — and say so
      explicitly in the README (trust signal). (Verified: no network/telemetry
      imports in `src/`; only `enrichment.py` uses `anthropic` for opt-in fix text.
      README "No network. No telemetry." paragraph added.)

---

## P1 — Launch-ready repo hygiene & distribution artifacts

**Community-health files**
- [x] `CODE_OF_CONDUCT.md` (Contributor Covenant). (v2.1; contact conduct@actaclad.com.)
- [x] `.github/ISSUE_TEMPLATE/bug_report.md`.
- [x] `.github/ISSUE_TEMPLATE/false_positive_report.md` — **your most important
      signal**; capture command, snippet, expected vs actual, version.
- [x] `.github/ISSUE_TEMPLATE/rule_request.md`.
- [x] `.github/PULL_REQUEST_TEMPLATE.md` — checklist: detector + bad fixture + good
      fixture + test; ADR if a decision is made. (+ DCO sign-off, config.yml routing.)
- [x] `CODEOWNERS`, `.github/FUNDING.yml`. (Owner `@actaclad`; FUNDING entries
      commented until accounts exist.)
- [ ] Issue **labels**: `good first issue`, `help wanted`, `false-positive`,
      `new-rule`, `precision`, `adapter`, `docs`. **(you, post-transfer: `gh label create`.)**

**Repo polish**
- [ ] **Social preview image** (Settings → Social preview).
- [ ] **About** sidebar text + **topics** (`static-analysis`, `llm`, `agents`,
      `ai-safety`, `reliability`, `python`, `sarif`, `linter`, `langchain`,
      `crewai`).
- [ ] Enable **Discussions** (Q&A, Show-and-tell, Ideas).
- [ ] First **GitHub Release** + tag from `CHANGELOG.md`.
- [x] **One-command dev setup** (dev container or `make dev`): clone → green tests
      in minutes. (`Makefile`: `make dev` + `make check`; documented in CONTRIBUTING.)

**Distribution artifacts (ship WITH launch)**
- [x] **GitHub Action** — 5-line `uses:` that scans + uploads SARIF to the Security
      tab. Highest-leverage artifact. (Composite `action.yml` at repo root →
      `uses: actaclad/plumbline@v1`; chose in-repo over a separate
      `actaclad/plumbline-action` so the version pin matches the package.)
- [x] **`pre-commit` hook** — publish `.pre-commit-hooks.yaml`. (`id: plumbline`.)
- [x] **Automated PyPI publish on tag** — GitHub Actions trusted publishing (OIDC,
      no API tokens). (`.github/workflows/publish.yml`, on Release published.
      **TODO (you): configure the PyPI trusted publisher + `pypi` GH environment.**)
- [x] **Docs page: "SARIF → GitHub code scanning"** — concrete demoable hook.
      (`docs/sarif-code-scanning.md`; linked from README.)

**Supply-chain credibility**
- [x] Dependabot enabled; deps pinned. (`.github/dependabot.yml`: pip +
      github-actions, weekly, grouped. Runtime deps are intentionally minimal
      lower-bounds — correct for a distributed library; Dependabot watches the
      rest. Actions pinned to major tags and Dependabot-tracked.)
- [~] Signed releases / OIDC publish; (later) SBOM + OpenSSF Best Practices badge.
      (OIDC publish done in `publish.yml`; SBOM + OpenSSF badge are later items.)

---

## P2 — Launch execution

**Assets**
- [ ] **60–90s terminal demo** (asciinema GIF/video) of a real before/after scan.
- [ ] **Launch blog post** — leads with the reliability wedge + the "flying blind"
      story; honest about limitations.
- [ ] **Before/after scan on a recognizable repo** as a shareable artifact.
- [ ] **Pin 2–3 `good first issue`s** for launch-day contributors.

**Pre-stage**
- [ ] **Soft-launch to 10–20 friendly agentic devs**; watch them run it cold on
      their own repos; fix every FP / friction they hit before going wide.

**Go wide (Tue–Thu US morning; be present in comments all day)**
- [ ] **Show HN** — problem-first, contrarian (reliability ≠ security), radically
      honest about limits.
- [ ] **Reddit:** r/LLMDevs, r/LocalLLaMA, r/Python (frame as "I built X for Y").
- [ ] **X/Twitter thread** with the real before/after scan.
- [ ] **Framework Discords** (LangChain, LlamaIndex, CrewAI) — useful, not spammy.
- [ ] **Product Hunt** (secondary) + **dev.to/Hashnode** cross-post (SEO).

---

## P3 — First 90 days (community foundation)

- [ ] **Responsiveness system** — triage labels + a routine: respond to every
      issue/PR within ~24h, even "thanks, looking." (Optional: welcome-bot,
      gentle stale-bot.)
- [ ] **Convert every FP report into a fix + regression test** — visibly. This is
      the brand.
- [ ] **`GOVERNANCE.md`** — who maintains, how PRs are reviewed, the no-rug-pull
      commitment.
- [ ] **Public `ROADMAP.md` / GitHub Projects board** — recruit contributors to
      specific items.
- [ ] **Seed ~8–10 `good first issue` rules** from the roadmap, each linking the
      rule-authoring guide + a rule to copy.
- [ ] **Land the first external contributor** (personally shepherd it — a
      trajectory-changing milestone).
- [ ] **all-contributors bot** + release-note shout-outs + `MAINTAINERS.md` path.
- [ ] **Publish the rule catalog as a browsable site** (GitHub Pages / MkDocs) —
      SEO + credibility + contribution surface.
- [ ] **2–3 content pieces:** the comparison page (vs agentic-radar/Agent Audit),
      the standards-coverage matrix, the honest "measured precision + known
      weaknesses" page.
- [ ] **Document the rule-stability promise** publicly (new rules ship advisory,
      gate only after measured precision) — removes the upgrade-breaks-CI fear.
- [ ] **Lead onboarding with baselines** (adopt on a dirty repo, gate only new
      findings) — removes the #1 adoption objection.

---

## P4 — Ongoing growth & sustainability

- [ ] **Get listed** in awesome-llmops / awesome-ai-agents / awesome-static-analysis.
- [ ] **Integrations as distribution** — framework docs, CI marketplaces, LangSmith
      / observability ecosystems.
- [ ] **VS Code extension** (consumes SARIF — sticky design-time feedback).
- [ ] **Docker image** + **Homebrew tap** + `uvx` support.
- [ ] **Predictable release cadence** (small, regular; automate changelog) — signals
      life.
- [ ] **Metrics dashboard:** PyPI downloads + retention, Action usage, unique repos
      scanned, FP-report trend, contributor count, time-to-first-response.
- [ ] **Attribution plumbing:** UTM docs→AgentGuard links + privacy-respecting
      analytics (e.g. Plausible); report OSS→pipeline contribution internally.
- [ ] **LiteLLM adapter** (recall) + **TOOL-001 / SEC-004 precision tuning** — the
      v0.2 detection work the real-repo validation surfaced.
- [ ] **Reach `1.0`** once the rule/Finding contract is stable — signals "safe to
      depend on."
- [ ] **Guard the wedge** — keep saying no to scope creep that dilutes the
      reliability/architecture focus.
- [ ] **Crisis playbook** — responsible disclosure for bugs in Plumbline; fast,
      honest response to negative threads (fix in public).
