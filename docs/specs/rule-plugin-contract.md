# Spec: Rule-Plugin Contract

**Status:** authoritative for how rules are written and discovered.
**Read alongside:** ADR-0001 (D6), `CONTRIBUTING.md`.

This is the contract Claude Code and contributors implement every rule against.
Stability matters: changing this contract requires an ADR, because every rule
depends on it.

---

## 1. Shape of a rule module

A rule is one Python module at `src/plumbline/rules/<cat>/<rule_id>.py`
(e.g. `rules/res/plb_res_001.py`). It exposes a rule object/class with:

```
RULE = Rule(
    id            = "PLB-RES-001",
    title         = "LLM/tool call without timeout",
    category      = "RES",
    pillar        = Pillar.Reliability,
    severity      = Severity.Blocker,
    confidence    = Confidence.High,
    standards     = ["NIST-AI-RMF:MANAGE"],
    why_it_matters= "A model/tool call with no timeout can hang indefinitely "
                    "and exhaust the worker pool, taking the service down.",
    remediation   = REMEDIATION,   # static text, with bad/good examples
    detect        = detect,        # the detector function
)
```

The `detect` function signature:

```
def detect(ctx: AnalysisContext) -> list[Finding]: ...
```

`AnalysisContext` provides (read-only):
- `ctx.ast`        — the parsed AST / libcst tree for the file
- `ctx.framework`  — normalized framework annotations (LLM_CALL, AGENT_LOOP, …)
- `ctx.taint`      — the source→sink reachability graph
- `ctx.file`       — path
- `ctx.config`     — effective config (for thresholds a rule may read)
- helpers to build a `Finding` with the rule's metadata pre-filled

A detector MUST:
- be pure: no I/O, no network, no clock, no randomness;
- be idempotent: same ctx → same findings;
- emit Findings only via the provided helper (so metadata + fingerprint are
  consistent);
- never raise for normal code; defensive `try` only around genuinely uncertain
  AST shapes, and on failure return `[]` (the engine logs analyzer errors).

## 2. Discovery (no central registry)

Rules are discovered by importing every module under `rules/**` and collecting
their `RULE` objects. Adding a rule = adding a module. There is NO hand-edited
list to append to (avoids contributor merge conflicts — ADR-0001 D6). Duplicate
IDs are a hard error at load time.

## 3. Fixtures (mandatory, no exceptions)

For rule `PLB-RES-001`, under `fixtures/PLB-RES-001/`:
- `bad_*.py` — at least one; MUST produce the finding.
- `good_*.py` — at least one; MUST NOT produce the finding.

Fixtures use realistic framework code, not toy snippets, so they double as
documentation of the pattern. The test harness asserts bad→fires, good→silent.

## 4. Confidence discipline

- `High` — deterministic, measured precision ~90%+ recorded in `/benchmark`.
  Gates builds. Use only when false positives are genuinely rare.
- `Medium` — strong heuristic; advisory by default; does not gate unless the
  user opts in.
- `Low` — informational; EXCLUDED from scoring.

If you cannot measure precision yet, ship Medium. Promoting to High later is an
easy PR; shipping a noisy High and breaking users' CI is a reputation hit.

## 5. Remediation text

`remediation` is static text containing a brief explanation plus a **bad** and a
**good** code example. The optional AI layer may, at output time only, tailor
this to the user's specific code — but the static text must stand alone and be
correct without the AI. Detection never depends on it.

## 6. Standards mapping

`standards` is a list of stable identifiers. Maintain the master mapping in
`docs/standards-map.md` (the coverage matrix). Use:
- `OWASP-LLM01`..`OWASP-LLM10` (LLM Top 10 2025)
- `OWASP-AGENTIC-*` (Agentic Top 10 2026)
- `NIST-AI-RMF:<function>` (GOVERN/MAP/MEASURE/MANAGE)
- `CWE-<n>`
Reliability/architecture rules may legitimately have no external standard —
use `[]`. That gap is Plumbline's opportunity (ADR-0001 D7), not a defect.

## 7. Worked example — PLB-RES-001 (the M1 reference rule)

This is the rule built end-to-end first; treat it as the template.

**Detector logic (plain English):**
For each `ctx.framework` node tagged `LLM_CALL` or `TOOL_HTTP_CALL`:
- determine whether a `timeout` is set, either as a keyword argument on the call
  or as a configured default on the client object that originates the call;
- if no timeout is resolvable, emit a Finding at the call site.

**bad fixture (must fire):**
```python
from openai import OpenAI
client = OpenAI()
def summarize(text):
    # no timeout anywhere → PLB-RES-001
    return client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": text}]
    )
```

**good fixture (must stay silent):**
```python
from openai import OpenAI
client = OpenAI(timeout=30)   # client-level timeout resolvable
def summarize(text):
    return client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": text}]
    )
```

**Edge cases the test should cover:**
- timeout set on the call vs. on the client (both → silent)
- timeout read from a variable/config (resolvable constant → silent;
  unresolvable → still fire, but this is where confidence honesty matters)
- non-LLM HTTP calls unrelated to the framework → not in scope, no finding

Build this rule, its fixtures, and its test as the proof that the whole pipeline
(AST → adapter → taint/framework context → rule → Finding → CLI + SARIF) works.
Everything else scales from this pattern.
