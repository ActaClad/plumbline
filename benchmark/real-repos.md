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

**Recall gap — FIXED.** `semantic_node_count: 0` because babyagi drives the model
through **LiteLLM**, which had no adapter. Added one (`adapters/litellm.py`):
babyagi now detects **16** calls and surfaces only true positives (triaged) —
GOV-002 ×14 (it `print()`s full LLM responses in its draft packs), COST-001 ×12
(no `max_tokens`), MDL-001 ×8 (scattered model literals). Remaining residual:
`instructor`, raw `requests`/`httpx` to an LLM endpoint, and other wrappers are
still invisible — Plumbline now sees raw OpenAI/Anthropic SDK, LangChain, CrewAI,
and LiteLLM.

### simonw/llm @ `0d593ea` (49 files)
| Rule | Count | Verdict |
|---|---|---|
| OUT-001 (unguarded JSON parse) | 2 | **TRUE POSITIVE** — `json.loads(tool_call.function.arguments)` parses model-generated function-call JSON with no guard; malformed arguments crash it. |
| OBS-001 (no tracing) | 1 | True (advisory) — no in-code tracing; the rule self-discloses the env-var blind spot. |

No false positives. 12 LLM calls correctly detected via the raw OpenAI adapter.

## Library (pattern discovery, not a precision measurement)

### crewAIInc/crewAI @ `d80719d` (1226 files, 1931 semantic nodes)
| Rule | Count → after fix | Class verdict |
|---|---|---|
| TOOL-001 | 86 → **1** | **FP class — FIXED.** The tools *do* declare schemas (via `args_schema=create_model(...)` to `super().__init__`, or a typed `_run`); the detector only saw class-body `args_schema=`. Fix: recognize `args_schema` referenced anywhere + typed `_run`; only flag *concrete* tools (those with a `_run`, not abstract bases); skip tools in test files. The 1 survivor (`ZapierActionTool`, `_run(self, **kwargs)`) is a defensible true positive. |
| SEC-004 | 26 → **0** | **FP class — FIXED.** All were test fixtures (`access_token="test_token"`, `jwt_token="aaaaa.bbbbbb.cccccc"`, contextvar tokens). Fix: dummy-marker substring + absolute distinct-char entropy + test-path suppression of the fuzzy heuristic (provider-pattern keys still fire everywhere). |
| COST-001 / MDL-001 / SEC-007 | 7 / 3 / 2 | Mixed; not individually triaged (library artifact). |

## Outcome

**All four FP/recall classes the first validation found are now fixed:**

- **SEC-005 non-DB `.execute()`** — requires a SQL keyword in the query arg
  (`executor.execute(name)` silent; real queries fire). babyagi: clean.
- **TOOL-001 crewAI schema mechanisms** — typed `_run` / dynamic `args_schema` /
  concrete-only / test-path. crewAI: 86 → 1 (a real TP).
- **SEC-004 test-fixture secrets** — substring placeholder + entropy + test-path.
  crewAI: 26 → 0.
- **LiteLLM recall gap** — new adapter. babyagi: 0 → 16 nodes, all true positives.

Every High-confidence corpus TP held at 100% through all four fixes; each fix
shipped with a regression fixture/test.

**Honest read & what's left.** On the real apps, the false positives found are
fixed and the survivors are true positives. But this is still only 3 repos — per
the precision-before-publicity gate, the P0 launch blocker is cleared when the
**new-FP-class discovery curve flattens across a larger, app-weighted set** (the
next batch of real repos). Fixing the first three classes is necessary, not yet
sufficient; "hardened" is now meaningfully closer to "validated."
