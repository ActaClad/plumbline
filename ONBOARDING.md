# Onboarding — understand & test Plumbline

Welcome! This guide gets a new teammate from zero to *"I understand what this is
and I've run it myself"* in about 30 minutes. Follow it top to bottom.

> TL;DR: Plumbline is a **static analyzer for LLM / agentic code**. It reads your
> Python source (no running it, no network) and flags reliability, architecture,
> harness, and security defects — the reasons agents fall over in production.

---

## 1. Understand what it is (10 min reading)

Read these, in order. Don't skip the first two — they explain *why* the project
is shaped the way it is, and that shape is deliberate.

1. **[`README.md`](README.md)** — the problem, the positioning, what it checks,
   and the quickstart. Start here.
2. **[`CLAUDE.md`](CLAUDE.md)** — the "project constitution": the non-negotiable
   principles. The load-bearing ones to internalize:
   - **Detection is deterministic** — same code in, same findings out. No
     network, no randomness in the analysis. (An optional AI layer only enriches
     *fix text*.)
   - **Dataflow over pattern-matching** — it tracks untrusted data from sources
     to dangerous sinks, it's not grep.
   - **False positives are the enemy** — every finding has a confidence level
     (High / Medium / Low); we'd rather miss than cry wolf.
   - **Reliability leads, security is a competent pillar** — this is *not*
     "another security scanner."
3. **[`docs/adr/0001-foundational-decisions.md`](docs/adr/0001-foundational-decisions.md)**
   — the founding decisions and the reasoning behind them (skim).
4. **[`docs/specs/rule-catalog.md`](docs/specs/rule-catalog.md)** — the actual
   list of rules (`PLB-<CATEGORY>-<NNN>`) across the four pillars.

**Mental model:** the engine parses code into an AST, runs a taint/dataflow pass,
then each **rule** is a small self-contained detector that reports **Findings**.
Findings are rolled up into a pass/fail **Quality Gate** (what you wire into CI)
and a 0–100 **Readiness Score** (a dashboard, not the gate).

---

## 2. Set it up (5 min)

Requires **Python 3.11+**, `git`, and `make`.

```bash
git clone https://github.com/durairajv/plumbline
cd plumbline
make dev      # creates .venv and installs everything (dev + AI extras)
```

`make dev` is the one-command setup. If you'd rather do it by hand, see the
"Dev setup" section of [`CONTRIBUTING.md`](CONTRIBUTING.md).

Activate the environment for the commands below:

```bash
source .venv/bin/activate
```

---

## 3. Test it — confirm the build is healthy (2 min)

```bash
make check
```

This runs exactly what CI runs: lint (`ruff`), format check, type check
(`mypy`), and the full test suite. You should see **all tests passing**
(~378 tests at time of writing) and no lint/type errors.

Run pieces individually if you want:

```bash
make test        # just the test suite (pytest)
make lint        # ruff
make typecheck   # mypy
```

**How the tests are structured (worth knowing):** every rule has two fixtures —
a `bad_*.py` that MUST trigger the rule and a `good_*.py` that MUST NOT. They
live in [`fixtures/<RULE_ID>/`](fixtures/), and the tests assert the detector
fires on the bad ones and stays silent on the good ones. That bad/good pairing is
the core quality discipline — it's how we keep false positives down.

---

## 4. Try it on real code — see it work (5 min)

List the rules that are loaded:

```bash
plumb rules        # ~20 rules across the four pillars
```

Scan a deliberately-broken fixture and read the output:

```bash
plumb scan fixtures/PLB-RES-001/
```

You'll see findings like `Major/High PLB-COST-001 ...:8` — each one tells you
**what**, **where** (file:line), **severity/confidence**, **why it matters** (the
concrete production failure), and **how to fix it**.

Now scan a *clean* file and watch it stay quiet (low false positives in action):

```bash
plumb scan fixtures/PLB-RES-001/good_call_timeout.py
```

Generate the standards-grade outputs (these are what tools/CI consume):

```bash
plumb scan fixtures/ --sarif out.sarif --json out.json --html report.html
open report.html      # self-contained offline report (use xdg-open on Linux)
```

Point it at any Python LLM/agent project you have lying around:

```bash
plumb scan /path/to/some/agent/project
```

> Tip: the harness rules (eval/observability) reason about the *whole repo*, so
> scan the **project root** (including `tests/` and CI), not just `src/`.

---

## 5. Where to go next

- **Want to understand a specific finding?** Look up its rule ID in
  [`docs/specs/rule-catalog.md`](docs/specs/rule-catalog.md) and open the rule's
  module under `src/plumbline/rules/<category>/`.
- **Want to add a rule?** [`CONTRIBUTING.md`](CONTRIBUTING.md) +
  [`docs/rule-authoring.md`](docs/rule-authoring.md). One rule = one detector +
  one bad fixture + one good fixture + a test. It's an afternoon.
- **Want the architecture?** [`docs/specs/`](docs/specs/) (architecture, the
  Finding model, the rule-plugin contract, adapters).
- **Curious how findings map to standards?** [`docs/standards-map.md`](docs/standards-map.md)
  (OWASP LLM / OWASP Agentic / NIST AI RMF / CWE).

## Two things to know about contributing here

- **Sign your commits** with `git commit -s` (we use the DCO — see CONTRIBUTING).
  A CI check enforces it on every PR.
- **Keep diffs small and reviewable.** The repo is built in tight increments on
  purpose.

Questions? Open a GitHub Discussion, or ping the team. Welcome aboard.
