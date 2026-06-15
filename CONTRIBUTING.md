# Contributing to Plumbline

Thanks for helping build the reliability and architecture analyzer for agentic
systems. This guide gets you from clone to merged rule.

## Principles you are signing up for

Before contributing, read [`CLAUDE.md`](CLAUDE.md) (the project constitution) and
[`docs/adr/0001-foundational-decisions.md`](docs/adr/0001-foundational-decisions.md).
The load-bearing ones:

1. **Detection is deterministic.** No network, clock, or randomness in the
   detection path. Same code → same findings, always.
2. **Dataflow over pattern-matching.** Prefer taint analysis; regex rules are
   the exception and must be justified.
3. **No noisy rules.** A rule ships as High confidence only with a measured
   precision (~90%+). Otherwise Medium or Low.
4. **One rule = one detector + one failing fixture + one passing fixture.**
5. **Capture decisions.** Non-trivial design changes get an ADR in `/docs/adr`.

## Dev setup

One command — `make dev` creates `.venv` and installs everything:

```bash
git clone https://github.com/actaclad/plumbline
cd plumbline
make dev        # create .venv + install with dev/ai extras
make check      # everything CI runs: lint, format, types, tests
```

Prefer it by hand? The equivalent is:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest          # all tests green before you start
ruff check .    # lint clean
mypy src        # types clean
```

Run `make` (or `make help`) to see all targets.

## Adding a rule (the common case)

A rule lives entirely in three places. Copy an existing rule of the same
category as your template.

1. **The detector module** — `src/plumbline/rules/<category>/<rule_id>.py`
   Exposes rule metadata and a `detect(ctx) -> list[Finding]` function. Pulls
   from the shared AST/taint context; does not re-parse files itself.

2. **The fixtures** — `fixtures/<RULE_ID>/bad_*.py` and `good_*.py`
   - `bad_*.py` MUST trigger the finding (the vulnerable pattern).
   - `good_*.py` MUST NOT trigger it (the correct pattern).
   - Keep fixtures minimal and realistic — real framework usage, not toy code.

3. **The test** — `tests/rules/<category>/test_<rule_id>.py`
   Asserts the detector fires on every `bad_*` and stays silent on every
   `good_*`. Use the shared rule-test harness.

Then:

```bash
pytest tests/rules/<category>/test_<rule_id>.py
plumb scan fixtures/<RULE_ID>/bad_example.py   # eyeball the real output
```

Rules are discovered by convention — you do **not** edit a central registry.
Adding the module is enough for it to be picked up.

### Rule metadata checklist

Every rule must declare:

- [ ] Stable ID: `PLB-<CAT>-<NNN>` (don't reuse a retired number)
- [ ] Title, category, pillar
- [ ] Severity: Blocker / Critical / Major / Minor / Info
- [ ] Confidence: High / Medium / Low (High needs a `/benchmark` precision number)
- [ ] Standards mapping (OWASP LLM / OWASP Agentic / NIST AI RMF / CWE) or "none"
- [ ] One-line "why it matters" naming a concrete production failure
- [ ] A remediation template with a bad and a good code example

### Confidence — be honest

If your rule can produce false positives on legitimate code, it is not High
confidence. High confidence means it gates builds and breaks CI for thousands of
users — earn it with a precision measurement. When unsure, ship Medium.

## Adding a framework adapter

Adapters normalize a framework's API (LangChain, CrewAI, raw SDK, ...) into the
common semantic model the rules consume. See `docs/specs/adapter-contract.md`.
Adding an adapter widens coverage for many rules at once — high-value work.

## Sign your commits (DCO)

Plumbline uses the [**Developer Certificate of Origin**](https://developercertificate.org/)
(DCO) — a lightweight, sign-off-based alternative to a CLA. By signing off you
certify that you wrote the contribution (or have the right to submit it under the
project's Apache-2.0 license). There is no separate form to sign.

Add a `Signed-off-by` line to **every commit** by committing with `-s`:

```bash
git commit -s -m "PLB-RES-007: detect missing retry on tool call"
```

That appends a trailer using your `git config user.name` / `user.email`:

```
Signed-off-by: Jane Developer <jane@example.com>
```

A DCO check runs on every pull request; commits missing the sign-off will fail
it. To fix an existing branch, run `git rebase --signoff main` (or amend the last
commit with `git commit --amend -s --no-edit`) and force-push.

## Pull request checklist

- [ ] `pytest`, `ruff check .`, `mypy src` all clean
- [ ] New/changed rule has bad + good fixtures and a passing test
- [ ] Determinism: no network/clock/randomness in detection
- [ ] Confidence level justified (precision number if High)
- [ ] ADR added if a non-trivial design decision was made
- [ ] Docs updated (`rule-catalog.md`, and `standards-map.md` if mapped)
- [ ] All commits signed off (`git commit -s`) — DCO
- [ ] Commit message references the rule ID and any ADR

## What we will push back on

- Rules that are likely to be noisy shipped as High confidence.
- LLM calls in the detection path (remediation enrichment only — and optional).
- Large diffs that bundle unrelated changes — split them.
- New runtime dependencies without a one-line justification.
- "Security scanner" framing that competes with the reliability identity —
  security rules are welcome, security *positioning* is not the goal.

## Code of conduct

Be precise, be kind, assume good faith. We are engineers building a tool other
engineers will trust enough to gate their pipelines on. Act like it.
