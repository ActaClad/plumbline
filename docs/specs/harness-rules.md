# Spec: Harness-pillar rules (EVAL / OBS)

**Status:** authoritative for EVAL-001 and OBS-001 (implemented, M5). EVAL-003 is
**proposed/deferred** pending ADR-0013 approval. Read alongside ADR-0010
(project scope), ADR-0013 (non-Python evidence).

These rules answer the harness-engineering question — *"is there scaffolding
around the model, or are you flying blind?"* They are **project-scope** absence
rules: they fire when LLM/agent code exists but a required harness signal is
**absent** anywhere in the scanned tree. That makes them the inverse of every
other rule, with two structural consequences:

1. **Scan scope is load-bearing.** An absence rule reasons about the whole
   project from whatever path it was given. `plumb scan ./src` cannot see
   `tests/` or CI, so it would fire falsely. Therefore: every harness finding
   carries an explicit *"these rules need the repo root scanned (tests/, CI),
   not just src/"* caveat, and they ship **Medium / advisory** — never gating.
2. **Detection recall = rule precision.** If we fail to recognize a real eval
   suite / tracing setup, we wrongly claim absence (a false positive). So
   evidence recognition is deliberately **broad**, and the rules err toward
   silence (CLAUDE.md §1.4).

A rule fires only when the project has LLM/agent code at all — i.e. some file's
`SemanticIndex` carries an `LLM_CALL`, `AGENT_CREATE`, or `AGENT_INVOKE` tag.
Findings anchor to the first `LLM_CALL` in sorted file order (ADR-0010 D2 —
"this is the code you are shipping blind").

---

## PLB-EVAL-001 — No evaluation suite for LLM/agent code (Major / Medium)

The defining harness defect: model behavior changes ship unverified.

**Evidence that an eval suite exists (any one ⇒ silent):**
- A file imports a known **LLM-evaluation framework** (`deepeval`, `ragas`,
  `langsmith`/`langchain.evaluation`, `trulens`/`trulens_eval`, `inspect_ai`,
  `phoenix.evals`/`arize`, `mlflow` eval, `braintrust`, `promptfoo` runners).
- A **test file** (`test_*.py`, `*_test.py`, under a `tests/` dir, or
  `conftest.py`) that **imports a module the project knows carries LLM/agent
  semantics** — i.e. it exercises the LLM paths, not merely "a test exists."
  This is the knife-edge: a repo with `test_utils.py` and no LLM-touching test
  still fires.

Cross-file matching uses `ProjectContext`: collect the module names of every
file with LLM/agent semantics (full dotted path + bare stem), then check each
candidate test file's import map (`SourceTree.imports[*].module`) for a suffix
match. No new substrate — the import map and per-file semantics already exist.

**Fires when:** LLM/agent code exists AND no eval-framework import anywhere AND
no LLM-touching test file. Anchored to the first `LLM_CALL`.

## PLB-OBS-001 — No tracing/instrumentation configured (Major / Medium)

An LLM/agent app with no tracing is undiagnosable in production.

**The blind spot (stated in the finding itself):** tracing is frequently enabled
*out of code* — `LANGCHAIN_TRACING_V2=true` (LangSmith), `opentelemetry-instrument`
/ `OTEL_*` auto-instrumentation. Static analysis cannot see env-var activation.
So OBS-001 is the **shakiest** harness rule; its finding explicitly says *"if you
enable tracing via env vars / auto-instrumentation, ignore this."*

**Evidence that tracing exists (any one ⇒ silent), broad on purpose:**
- import of an observability SDK: `opentelemetry`, `langsmith`, `langfuse`,
  `phoenix`/`arize`, `helicone`, `traceloop`, `logfire`, `wandb`/`weave`,
  `braintrust`, `mlflow`;
- a framework tracing callback in code (LangChain `LangChainTracer` /
  `callbacks=`, CrewAI telemetry);
- an in-code reference to a tracing env var (`LANGCHAIN_TRACING_V2`, `OTEL_`),
  which at least shows intent.

**Fires when:** LLM/agent code exists AND none of the above appears anywhere.
Anchored to the first `LLM_CALL`. Ships Medium; the env-var blind spot is the
reason it is advisory and the reason its finding self-discloses.

## PLB-EVAL-003 — Prompt/model changes not gated by eval in CI (Major / Medium)

**Status: implemented** (ADR-0013 Accepted at the M5 review). Uses
`ProjectContext.evidence.ci_files` — the text of a fixed, closed set of known CI
config paths (`core/evidence.py`). EVAL-003 is a **sanctioned grep rule**
(CLAUDE.md §1.2, `grep_rule=True`): dataflow does not apply to CI YAML, so it
scans CI text for a test/eval invocation token (`pytest`, `tox`, `nox`, an
eval-framework name, `make test`, an `eval`/`evals` target, …).

**Fires when:** LLM/agent code exists, ≥1 CI file exists, and **no** CI file text
contains a test/eval token. It deliberately stays silent when there is **no CI at
all** — that case is EVAL-001's ("no eval suite"), not this rule's. Anchored to
the first `LLM_CALL`; carries the scan-scope caveat; Medium/advisory. Its
marginal signal over EVAL-001 is precisely "you have evals but CI doesn't run
them" (ADR-0013 D3).

## Deferred from M5 (backlogged with reasons)

- **PLB-EVAL-002 (no golden dataset / ground-truth)**: distinguishing a test
  that asserts against reference outputs from one that only asserts "it ran" is
  genuinely noisy statically (assertions take countless shapes; golden data may
  be inline, in fixtures, or external). High false-positive surface — defer
  until a precise signal exists.
- **PLB-OBS-002 (no run/session/user IDs on calls)**: correlation IDs are
  usually injected via middleware/context/callbacks, not call kwargs — so this
  shares OBS-001's env/middleware blind spot with less payoff. Defer.
