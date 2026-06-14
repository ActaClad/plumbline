# Real-repo validation (v0.1)

Every "100% precision" elsewhere in `/benchmark` is measured on a corpus and a
realistic app **authored by the same agent that wrote the rules** — so it can
only surface false positives we already thought to construct. This is the
counterweight: scan real open-source code and triage every finding by hand.

**Method.** Shallow-clone real OSS Python at a pinned commit, `plumb scan`, and
classify each finding TP/FP from the source. Plumbline does static AST analysis
only — it never imports or runs the scanned code (the determinism firewall) — so
scanning untrusted repos is safe. The third-party source is **not** vendored;
only this triage is committed. No headline precision % is reported: with a tiny
sample and an app-vs-library skew, a single number would be false precision.
Read the findings and their verdicts; the denominator is visible.

**App vs library.** A *library* (crewAI) is mostly `tests/` + internal tool
implementations a user's app does not have, so its raw counts are inflated — it
is **pattern discovery**, not a precision measurement. The precision read comes
from the small real *apps* (babyagi, `llm`).

## Apps

### yoheinakajima/babyagi @ `fa8930e` (40 files)
| Rule | Count | Verdict |
|---|---|---|
| SEC-005 (SQLi) | 2 | **FALSE POSITIVE** — `g.functionz.executor.execute(function_name, …)` is a *function* executor, not a DB cursor; `function_name` is request input. Fixed (see below). Re-scan: **0 findings**. |

**Recall gap:** `semantic_node_count: 0` — babyagi drives the model through
**LiteLLM**, which is not a supported adapter, so none of its LLM calls were
detected. A user on an unsupported stack (LiteLLM, `instructor`, raw `requests`)
gets silent under-coverage. Plumbline sees raw OpenAI/Anthropic SDK, LangChain,
and CrewAI; everything else is invisible. (Backlogged.)

### simonw/llm @ `0d593ea` (49 files)
| Rule | Count | Verdict |
|---|---|---|
| OUT-001 (unguarded JSON parse) | 2 | **TRUE POSITIVE** — `json.loads(tool_call.function.arguments)` parses model-generated function-call JSON with no guard; malformed arguments crash it. |
| OBS-001 (no tracing) | 1 | True (advisory) — no in-code tracing; the rule self-discloses the env-var blind spot. |

No false positives. 12 LLM calls correctly detected via the raw OpenAI adapter.

## Library (pattern discovery, not a precision measurement)

### crewAIInc/crewAI @ `d80719d` (1226 files, 1931 semantic nodes)
| Rule | Count | Class verdict |
|---|---|---|
| TOOL-001 | 86 | **FP class** — the tools *do* declare schemas, via `args_schema = create_model(...)` passed to `super().__init__`, or a typed `_run(self, x: T)` signature; the crewAI adapter only recognizes a *class-body* `args_schema =` assignment. Backlogged. |
| SEC-004 | 26 | **FP class** — test fixtures with fake secrets (`access_token = "test_token"`, `jwt_token = "aaaaa.bbbbbb.cccccc"`, one already `# noqa: S105`). The placeholder allow-list is too narrow. Backlogged. |
| COST-001 / MDL-001 / SEC-007 | 7 / 3 / 2 | Mixed; not individually triaged (library artifact). |

## Outcome

- **Fixed (this pass): SEC-005 non-DB `.execute()`.** It now requires a SQL
  keyword in the query arg's literal/f-string parts — `executor.execute(name)`
  stays silent, a real interpolated query still fires (corpus TP preserved at
  100%). The babyagi false positives are gone.
- **Backlogged with concrete examples:** TOOL-001 schema-mechanism recognition
  (typed `_run`, dynamic `args_schema`); SEC-004 test-fixture secrets (entropy +
  broader placeholder/test-path awareness); the LiteLLM/unsupported-stack recall
  gap.
- **Honest read:** on the two real apps, the only false positives were the
  SEC-005 cluster, now fixed; the rest were true positives or legitimate
  advisories. The library scan shows the precision *classes* that still need work
  before a wide release. "Hardened" is now closer to "validated", but full
  external validation across a larger, app-weighted set remains v0.2 work.
