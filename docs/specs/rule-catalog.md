# Plumbline — Canonical Rule Catalog (Reliability-Led)

**Package:** `actaclad-plumbline` · **CLI:** `plumb` · **Rule prefix:** `PLB-`
**One-line identity:** *The reliability and architecture analyzer for LLM and agentic systems.*
**This document supersedes:** the earlier security-led v1 catalog.
**Scope discipline:** broad taxonomy, narrow launch — ~40 rules in v1, the rest published as roadmap.

---

## 1. Positioning

### 1.1 The market gap

Every existing static analyzer in the AI-code space is a **security scanner** — agentic-radar, Agent Audit, ZIRAN, SkillFortify, MEDUSA. They all ask the same question: *"Is this code dangerous?"* They all map to the OWASP Agentic Top 10. They are converging on the same taxonomy and competing on false-positive rate within the security frame.

That leaves an entire dimension uncovered. **Most agentic systems do not fail because they were attacked. They fail because they were badly engineered** — a runaway agent loop, no fallback when a provider 429s, no retry, unbounded memory growth, a silent model swap that changed behavior, an `eval` of model output that breaks on the first unexpected token, no verification node so an early error propagates to the final answer.

These are **reliability and architecture defects**, and no static analyzer is checking for them.

### 1.2 The position

> **Plumbline asks a different question than the security scanners. They ask "is this code dangerous?" Plumbline asks "will this system fall over in production?"**

Plumbline is the static analyzer that checks whether an LLM/agentic application is built on sound **reliability engineering**, proven **architectural patterns**, and modern **harness engineering** — the engineering scaffolding around the model (evaluation harnesses, fallback structure, verification nodes, ground-truth checks, observability instrumentation, golden-dataset test suites).

Security is **one pillar** of a well-engineered system. Plumbline covers it competently — but it is table stakes, not the headline. The headline is: *your agentic system is one untested deploy away from a production incident, and Plumbline gives you the static proof before it happens.*

### 1.3 Why this is defensible

- **Uncontested space.** The security scanners cannot easily pivot here — reliability/architecture analysis is a different rule design philosophy (correctness patterns, not threat taint), and their identity is "security." They would have to become a different product.
- **Plays to the founder's strength.** A 20-year architect's natural product is an architecture/reliability checker, not a pentest tool. This competes on home turf.
- **Painkiller, not vitamin.** "Will it fall over in production" maps to a fear buyers already have. "Architecture quality" alone reads as a vitamin; reliability framing makes it urgent.
- **Closes the loop to the runtime platform.** Reliability defects are exactly what production traces reveal. The static linter flags the *risk*; the AgentGuard runtime platform confirms the *incident*. Natural Phase 1 → Phase 2 bridge.

### 1.4 Positioning guardrails (for customer discovery)

- **Lead with the concept, not the buzzword.** Say "the engineering scaffolding around the model" — let them nod — *then* name it "harness engineering" if useful. Never open with vocabulary the buyer must be taught.
- **Broad taxonomy, narrow launch.** The catalog below shows the full architectural surface. v1 ships ~40 rules, deliberately weighted *away* from the crowded security space toward Resilience, Agent Control Flow, and harness engineering.
- **Discovery question is now comparative.** Not "would you want this" but: *"agentic-radar and Agent Audit are free and cover security — what would make you adopt a tool that covers reliability and architecture instead?"* If there's no crisp answer, that is the signal.

---

## 2. Product principles (unchanged — they are correct)

1. **Detection is deterministic. Remediation may use AI.** The rule engine is pure static analysis (AST + dataflow). An LLM may only generate context-aware fix text — never decide whether an issue exists.
2. **Dataflow over pattern-matching.** The core engine is a taint/dataflow tracker. Grep-style rules are the exception.
3. **Every finding carries a confidence level.** High = deterministic, safe to fail a build. Medium = advisory default. Low = informational, excluded from scoring. Sub-90% precision → never ships as High.
4. **The Quality Gate is the product; the Readiness Score is the marketing.** Teams wire the gate into CI. The score is a stakeholder roll-up.
5. **Ship small and correct.** Python only, 3–4 frameworks, ~40 High/Medium-confidence rules. A linter right 40 times beats one noisy 200 times.

---

## 3. Core architecture (unchanged)

```
  Source code → Python AST (ast / libcst)
       → Framework adapter layer (raw OpenAI/Anthropic SDK, LangChain/LangGraph, CrewAI)
       → Taint / dataflow engine (sources → sinks)
       → Rule engine (detector functions → Findings)
       → Scoring + Quality Gate + Reporters (CLI, SARIF, JSON, HTML, GitHub annotations)
```

Build the taint engine first. SARIF output is non-negotiable. The framework adapter layer matters because reliability rules — like agent-loop bounds — are framework-specific in shape.

---

## 4. Severity, confidence, scoring

Severity: **Blocker / Critical / Major / Minor / Info.** Confidence: **High / Medium / Low.**
Default Quality Gate: *zero Blockers AND zero High-confidence Criticals* — fully configurable.

**Four headline sub-scores — reordered to match the new position:**

1. **Reliability** (the lead — was not the lead before)
2. **Architecture & Agentic Maturity**
3. **Harness Engineering** (new headline pillar — evaluability, verification, observability scaffold)
4. **Security**

Suggested headline-score weights: Reliability 35%, Architecture & Agentic Maturity 25%, Harness Engineering 20%, Security 20%. Tune against real repos. Composite **Readiness Score** = weighted roll-up; dashboard/marketing only.

---

## 5. The 12 categories — re-grouped under the four pillars

| # | Category | Code | v1 depth | Pillar |
|---|---|---|---|---|
| 1 | Resilience & Fault Tolerance | `RES` | **Deep** | Reliability |
| 2 | Agent Orchestration & Control Flow | `AGT` | **Deep** | Architecture & Agentic Maturity |
| 3 | Model Lifecycle & Configuration | `MDL` | **Deep** | Reliability |
| 4 | Output Validation & Structured Generation | `OUT` | **Deep** | Reliability |
| 5 | Tool & Function Calling | `TOOL` | Partial | Architecture & Agentic Maturity |
| 6 | RAG & Knowledge Architecture | `RAG` | Partial | Architecture & Agentic Maturity |
| 7 | Prompt Engineering & Management | `PRM` | Partial | Architecture & Agentic Maturity |
| 8 | Evaluation & Verification Harness | `EVAL` | **Deep** | Harness Engineering |
| 9 | Observability & Instrumentation | `OBS` | Partial | Harness Engineering |
| 10 | Cost & Token Efficiency | `COST` | Partial | Reliability |
| 11 | Security & Adversarial Robustness | `SEC` | Partial | Security |
| 12 | Data Privacy & Governance | `GOV` | Partial | Security |

**What changed from the security-led catalog:** Resilience, Agent Control Flow, Model Lifecycle, Output Validation, and a new **Evaluation & Verification Harness** category are now the deep-investment areas. Security shrinks from 11 deep rules to a competent-but-not-headline pillar. The launch-40 is re-weighted accordingly.

---

## 6. v1 LAUNCH RULES (~40)

Format: **ID — Title** | Severity / Confidence | Mapping | What & why | Detection | Fix.

### Category 1 — Resilience & Fault Tolerance (`RES`) — PILLAR: Reliability

**PLB-RES-001 — LLM/tool call without timeout**
Blocker / High
A model or tool call with no timeout can hang indefinitely and exhaust the worker pool.
*Detection:* call to a known LLM/HTTP client with no `timeout` argument and no client-level timeout.
*Fix:* set an explicit timeout on the call or client.

**PLB-RES-002 — No retry on LLM/tool call**
Critical / High
Transient provider errors (429, 5xx) with no retry become avoidable user-facing failures.
*Detection:* LLM/tool call not wrapped in a retry construct and SDK auto-retry not configured.
*Fix:* exponential backoff with jitter (`tenacity`, or the SDK's `max_retries`).

**PLB-RES-003 — Retry without exponential backoff**
Major / High
Fixed-interval or immediate retries amplify load and worsen throttling.
*Detection:* retry construct present with constant/zero wait.
*Fix:* exponential backoff with jitter; cap total attempts.

**PLB-RES-004 — No fallback model or degraded path**
Critical / Medium
Single-provider dependency with no fallback means a provider outage is a full outage.
*Detection:* exactly one model/provider on the request path; no alternate branch on failure.
*Fix:* configure a fallback model or a graceful degraded response.

**PLB-RES-005 — Bare except swallowing LLM errors**
Critical / High
`except: pass` around a model call hides failures and corrupts downstream state.
*Detection:* try-block containing an LLM/tool call with a bare/overbroad handler that neither logs nor re-raises.
*Fix:* catch specific exceptions; log; return an explicit error result.

**PLB-RES-006 — No rate-limit (429) handling**
Major / High
*Detection:* LLM call path with no 429 branch and no retry library that handles 429.
*Fix:* handle 429 with backoff and a client-side limiter.

**PLB-RES-007 — Non-idempotent side effect inside a retried block**
Critical / Medium
A retried block performing a side effect (DB write, payment, email) can double-execute.
*Detection:* taint — a side-effecting sink reachable inside a retry-wrapped block with no idempotency key.
*Fix:* make the operation idempotent or move it outside the retried region.

**PLB-RES-008 — Unbounded conversation/memory growth**
Major / Medium
History appended every turn with no truncation eventually overflows context and inflates cost/latency.
*Detection:* a memory/list object appended in a loop or per-request handler with no trim/window/summarize.
*Fix:* sliding window, token-budget trim, or summarization buffer.

**PLB-RES-009 — No circuit breaker on a repeatedly-failing dependency**
Major / Low
A flaky tool/provider called in a hot path with no circuit breaker cascades failure under load.
*Detection:* a dependency called in a loop/high-frequency path with retry but no circuit-breaker construct.
*Fix:* add a circuit breaker to fail fast when a dependency is degraded.
*(Low confidence — advisory.)*

**PLB-RES-010 — Streamed response not used as a context manager**
Major / Medium
The SDK streaming helpers (`messages.stream`/`responses.stream`/`chat.completions.stream`) are context managers; used otherwise the HTTP connection is never guaranteed to close, exhausting the pool under load. (ADR-0018)
*Detection:* a `.stream()` helper call (SDK imported in-file) that is not the context expression of a `with`/`async with`. Does not touch `create(..., stream=True)` (often iterated to completion legitimately).
*Fix:* `with client.messages.stream(...) as stream: ...`.
*(Medium/advisory until a `/benchmark` precision pass.)*

### Category 2 — Agent Orchestration & Control Flow (`AGT`) — PILLAR: Architecture & Agentic Maturity

**PLB-AGT-001 — Agent loop without max-iteration limit**
Blocker / High | OWASP Agentic
An agent/executor loop with no iteration cap runs away — burning cost, never terminating.
*Detection:* agent constructed without `max_iterations`/equivalent; or a hand-rolled agent `while` loop with no counter bound.
*Fix:* set an explicit iteration cap with defined behavior on hitting it.

**PLB-AGT-002 — No termination/exit condition in custom agent loop**
Critical / High
*Detection:* a `while True` / recursive planner-executor with no reachable break/return tied to a goal/stop signal.
*Fix:* define an explicit completion condition and a hard stop.

**PLB-AGT-003 — Unbounded recursion in planner / sub-agent spawning**
Critical / Medium
*Detection:* a function that spawns/invokes sub-agents and can reach itself with no depth parameter or check.
*Fix:* pass and enforce a delegation/recursion depth limit.

**PLB-AGT-004 — No global timeout / token budget on the full agent run**
Critical / High
Per-call timeouts exist but the multi-step run is unbounded in wall-clock time and total tokens.
*Detection:* agent invocation with no run-level deadline or cumulative token budget.
*Fix:* enforce a total run deadline and a cumulative token budget.

**PLB-AGT-005 — No self-critique / verification node in a multi-step agent**
Major / Medium
Multi-step agents that never verify intermediate results propagate early errors into the final output. *(Promoted from Low to Major — this is a core reliability/harness defect, central to the new positioning.)*
*Detection:* agent graph/chain with no reviewing/validating/critique step between generation and final output.
*Fix:* add a critique/verification node or an output check before finalizing.

**PLB-AGT-006 — No human-in-the-loop gate before an irreversible action**
Major / Medium | OWASP Agentic
*Detection:* a high-impact action (delete, pay, send, modify external state) on an agent path with no interrupt/approval node.
*Fix:* insert an approval checkpoint before irreversible actions.

**PLB-AGT-007 — Agent state mutated without a defined reducer/merge strategy**
Minor / Low
Shared agent state written by multiple nodes with no defined merge strategy causes nondeterministic behavior.
*Detection:* multiple writers to a shared state object with no reducer/channel definition.
*Fix:* define explicit state reducers/channels (e.g., LangGraph state channels).
*(Low confidence — advisory.)*

**PLB-AGT-008 — AutoGen team with no turn cap or termination condition**
Major / Medium | OWASP LLM10 · CWE-835
Unlike CrewAI/LangChain, AutoGen's AgentChat teams have no default turn limit; a team with neither `max_turns` nor a `termination_condition` can loop forever. (ADR-0018)
*Detection:* an AutoGen team constructor (`RoundRobinGroupChat`/`SelectorGroupChat`/`Swarm`/`MagenticOneGroupChat`), SDK imported, with neither bound keyword. (Self-contained AST rule.)
*Fix:* set `max_turns=` or a `termination_condition=`.
*(Medium/advisory until a `/benchmark` precision pass.)*

### Category 3 — Model Lifecycle & Configuration (`MDL`) — PILLAR: Reliability

**PLB-MDL-001 — Hardcoded / unpinned model name**
Major / High
Scattered model-name literals make swaps error-prone and behavior drift untraceable. *(Promoted from Minor — silent model drift is a top reliability complaint from production.)*
*Detection:* model identifier as scattered string literals rather than a single config value.
*Fix:* centralize model IDs in config; pin explicitly.

**PLB-MDL-002 — Deprecated or sunset model identifier**
Critical / High
A deprecated model string is a scheduled production outage.
*Detection:* model string matching a maintained list of deprecated identifiers.
*Fix:* migrate to a supported model; re-run evaluations after switching.

**PLB-MDL-003 — High temperature on a tool-calling / agentic path**
Major / Medium
High sampling temperature on an agent selecting tools/actions makes action selection nondeterministic and untestable.
*Detection:* an LLM call with `temperature` above a threshold (e.g., > 0.3) where the same call has tools enabled.
*Fix:* lower temperature for action-selection calls; reserve higher values for creative generation.

**PLB-MDL-004 — No model-abstraction layer (direct provider lock-in)**
Major / Medium
Provider SDK called directly from many modules makes fallback (RES-004) and provider swaps impossible without a refactor. *(Promoted from Low/Minor — it is the structural precondition for fallback, a Reliability concern.)*
*Detection:* provider SDK called directly across many modules with no wrapper/interface.
*Fix:* introduce a thin model interface enabling fallback and provider swaps.

**PLB-MDL-005 — Model swapped with no evaluation gate**
Major / Low
A changed model identifier with no associated eval run is unverified behavior change shipped to production.
*Detection:* model config change in version control with no corresponding eval suite invocation in CI.
*Fix:* gate model changes behind an evaluation run (links to EVAL category).
*(Low confidence — advisory; requires CI/VCS context.)*

**PLB-MDL-006 — Removed sampling parameter passed to a reasoning model**
Critical / Medium
Reasoning models (OpenAI o-series & GPT-5; Anthropic Opus 4.7/4.8 & Fable-5) removed `temperature`/`top_p`/`top_k`; passing one returns HTTP 400 on every call. (ADR-0018)
*Detection:* resolved `model=` is in the curated `SAMPLING_UNSUPPORTED` table AND a removed param is provably present as an explicit keyword (a `**kwargs` spread is not flagged).
*Fix:* remove the sampling params; a reasoning model self-regulates sampling — steer with reasoning-effort controls.
*(Medium/advisory until a `/benchmark` precision pass, per the rule-stability promise.)*

**PLB-MDL-007 — Anthropic extended-thinking budget misconfigured**
Critical / Medium
Extended thinking requires `budget_tokens >= 1024` AND `budget_tokens < max_tokens`; either violation is HTTP 400 on every call. (ADR-0018)
*Detection:* literal comparison of the `thinking={...}` dict's `budget_tokens` against the 1024 floor and the `max_tokens` literal — fires only on provable integer literals.
*Fix:* set `1024 <= budget_tokens < max_tokens`.
*(Medium/advisory until a `/benchmark` precision pass.)*

**PLB-MDL-008 — OpenAI reasoning model uses max_tokens not max_completion_tokens**
Critical / Medium
o-series/GPT-5 reject `max_tokens` on Chat Completions; the required arg is `max_completion_tokens` — HTTP 400 otherwise. (ADR-0018)
*Detection:* resolved `model=` in `OPENAI_REASONING_MODELS` AND `max_tokens` provably present as an explicit keyword. Anthropic models are excluded (they require `max_tokens`).
*Fix:* rename the argument to `max_completion_tokens`.
*(Medium/advisory until a `/benchmark` precision pass.)*

### Category 4 — Output Validation & Structured Generation (`OUT`) — PILLAR: Reliability

**PLB-OUT-001 — LLM output parsed as JSON without error handling**
Critical / High
`json.loads` on raw LLM output with no guard crashes on the first malformed generation.
*Detection:* `json.loads`/equivalent applied to LLM output with no surrounding error handling.
*Fix:* validate against a schema; handle parse failure with retry or fallback.

**PLB-OUT-002 — LLM output used directly as control flow**
Major / Medium
Branching on raw model output (`if response == "yes"`) is brittle and injectable.
*Detection:* a conditional whose test is an unvalidated LLM output value.
*Fix:* constrain output to an enum/schema; validate before branching.

**PLB-OUT-003 — No handling for empty / refused / truncated output**
Major / High
Consuming LLM output with no check for empty content, refusal, or `finish_reason == length` produces silent downstream corruption.
*Detection:* LLM output consumed downstream with no finish-reason / empty / refusal check.
*Fix:* check finish reason and content; handle refusal and truncation paths.

**PLB-OUT-004 — Structured-output schema declared but not enforced**
Major / Medium
A schema/response-format is declared but the response is consumed without validation against it.
*Detection:* a call declaring a structured-output schema whose result is used without a validation step.
*Fix:* validate the response against the declared schema before use.

### Category 5 — Tool & Function Calling (`TOOL`) — PILLAR: Architecture & Agentic Maturity

**PLB-TOOL-001 — Tool defined without an input schema / typed signature**
Major / High
An untyped tool lets the model pass malformed arguments — a reliability defect before it is a security one.
*Detection:* a registered tool whose function lacks type annotations / a declared parameter schema.
*Fix:* declare a typed schema (Pydantic model / typed signature) for every tool.

**PLB-TOOL-002 — Tool arguments used without validation**
Critical / High
*Detection:* taint — a tool parameter flows to a sink (file, HTTP, SQL, shell) with no validation in between.
*Fix:* validate and constrain every tool argument before use.

**PLB-TOOL-003 — Tool has no error handling / can crash the agent run**
Major / Medium
An unhandled exception inside a tool aborts the whole agent run instead of degrading gracefully.
*Detection:* a tool implementation with external calls and no internal error handling that returns a structured error.
*Fix:* handle errors inside the tool; return a structured error the agent can reason about.

**PLB-TOOL-004 — Tool output returned to the model without sanitization**
Major / Medium | OWASP LLM01 (indirect injection)
*Detection:* taint — tool return value flows into a subsequent prompt with no sanitizing/delimiting step.
*Fix:* treat tool output as untrusted external content; delimit and isolate it.

### Category 6 — RAG & Knowledge Architecture (`RAG`) — PILLAR: Architecture & Agentic Maturity

**PLB-RAG-001 — Retrieval `k` unset or unreasonably large**
Major / Medium
*Detection:* retriever/vector-store query with no `k`/`top_k`, or a value above a configurable threshold.
*Fix:* set a deliberate `k`; tune for context budget and relevance.

**PLB-RAG-002 — Retrieved context not bounded against the context window**
Critical / Medium
Concatenating all retrieved chunks with no token budgeting causes context overflow / silent truncation.
*Detection:* retrieved documents joined into the prompt with no length/token check.
*Fix:* enforce a token budget for retrieved context; truncate deliberately.

**PLB-RAG-003 — No grounding / citation enforcement on RAG output**
Major / Low
A RAG pipeline that never checks the answer against retrieved context invites ungrounded hallucination.
*Detection:* a retrieve→generate chain with no grounding/citation/faithfulness check on the output.
*Fix:* add a grounding check or require citations tied to retrieved chunks.
*(Low confidence — advisory; sharpens greatly with trace data in Phase 2.)*

**PLB-RAG-004 — Embedding-model mismatch between index and query path**
Major / Medium
Indexing with one embedding model and querying with another silently destroys retrieval quality.
*Detection:* the embedding model used at index time differs from the one on the query path.
*Fix:* use the same embedding model for indexing and querying; pin it.

### Category 7 — Prompt Engineering & Management (`PRM`) — PILLAR: Architecture & Agentic Maturity

**PLB-PRM-001 — Untrusted input concatenated into a prompt without delimiting**
Critical / High | OWASP LLM01
*Detection:* taint — a tainted source reaches prompt text via raw concatenation/f-string with no delimiter or role separation.
*Fix:* place untrusted content in a separate message/role; wrap with explicit delimiters.

**PLB-PRM-002 — Hardcoded prompt string (not externalized/versioned)**
Minor / Medium
Inline prompt literals cannot be versioned, evaluated, or updated without a redeploy.
*Detection:* a substantial/multi-line string literal passed directly as prompt content.
*Fix:* externalize prompts to a managed store or versioned files.

**PLB-PRM-003 — No system prompt defined**
Minor / Medium
*Detection:* chat-completion call with no system message in the message construction.
*Fix:* add a system prompt establishing role, constraints, and refusal behavior.

### Category 8 — Evaluation & Verification Harness (`EVAL`) — PILLAR: Harness Engineering — NEW HEADLINE CATEGORY

**PLB-EVAL-001 — No evaluation suite present for LLM/agent code**
Major / High
A repo with LLM/agent code and no eval suite ships behavior changes blind. This is the defining harness-engineering defect.
*Detection:* repo contains LLM/agent code paths but no detectable evaluation/test suite targeting model behavior.
*Fix:* add an evaluation suite with golden datasets and regression checks.

**PLB-EVAL-002 — No golden dataset / ground-truth fixtures**
Major / Medium
Tests exist but assert only that code runs, never that outputs match expected results.
*Detection:* test files exercising LLM/agent code with no reference-output/golden-dataset fixtures.
*Fix:* add golden datasets with reference outputs; assert against them.
*(Directly addresses the founder's consulting observation: "no ground-truth verification.")*

**PLB-EVAL-003 — Prompt or model changes not gated by evaluation in CI**
Major / Medium
Prompts/models change but no eval runs on change — regressions reach production undetected.
*Detection:* prompt/model definitions change in VCS with no eval invocation in the CI pipeline.
*Fix:* wire the eval suite into CI; gate prompt/model changes on eval thresholds.

**PLB-EVAL-004 — Critical agent path with no assertion on intermediate steps**
Minor / Low
Multi-step agent tests assert only the final output, never intermediate tool calls or reasoning steps.
*Detection:* agent tests asserting only on final output, with no trajectory/intermediate-step assertions.
*Fix:* assert on intermediate tool calls and decisions, not just the final answer.
*(Low confidence — advisory.)*

### Category 9 — Observability & Instrumentation (`OBS`) — PILLAR: Harness Engineering

**PLB-OBS-001 — No tracing/instrumentation configured**
Major / High
An LLM/agent app with no tracing is unobservable in production — failures cannot be diagnosed.
*Detection:* LLM/agent code with no tracing callback, OpenTelemetry instrumentation, or observability SDK.
*Fix:* instrument with OpenTelemetry or an observability SDK.

**PLB-OBS-002 — No run/session/user identifiers attached to calls**
Minor / Medium
*Detection:* LLM/agent calls with no correlation IDs (run, session, user) propagated.
*Fix:* attach run/session/user IDs for traceability and per-user analysis.

**PLB-OBS-003 — Token usage / cost not captured**
Minor / Low
*Detection:* LLM calls with no capture of token-usage or cost metadata.
*Fix:* record token usage and cost per call for cost observability.
*(Low confidence — advisory.)*

### Category 10 — Cost & Token Efficiency (`COST`) — PILLAR: Reliability

**PLB-COST-001 — No max_tokens / output cap on generation**
Major / High
No output bound is both a cost risk and a latency/reliability risk.
*Detection:* generation call with no `max_tokens`/equivalent output bound.
*Fix:* set an explicit output token cap.

**PLB-COST-002 — Repeated identical LLM call with no caching**
Minor / Medium
*Detection:* an LLM call with provably constant inputs inside a loop, or a repeated call pattern with no cache layer.
*Fix:* cache deterministic calls; hoist invariant calls out of loops.

### Category 11 — Security & Adversarial Robustness (`SEC`) — PILLAR: Security (table stakes — competent, not headline)

**PLB-SEC-001 — Untrusted input reaches a tool-enabled prompt**
Blocker / High | OWASP LLM01→LLM02
The injection-to-action path: untrusted content flows into a prompt whose model can call tools.
*Detection:* taint — a tainted source reaches a prompt sink where the same call has tools configured.
*Fix:* isolate untrusted content with delimiting; gate tool execution; constrain tool scope.

**PLB-SEC-002 — LLM output passed to eval/exec/compile**
Blocker / High | CWE-95
*Detection:* taint — LLM output reaches `eval`, `exec`, `compile`.
*Fix:* never execute model output; if codegen is intended, sandbox with strict allow-listing.

**PLB-SEC-003 — LLM output passed to a shell command**
Blocker / High | CWE-78
*Detection:* taint — LLM output reaches `os.system`, `subprocess.*` with `shell=True`, `os.popen`.
*Fix:* avoid shell; use argument lists (no `shell=True`); validate against an allow-list.

**PLB-SEC-004 — Hardcoded API key or secret**
Blocker / High | CWE-798
*Detection:* string literals matching provider key patterns, or assignment of a literal to `api_key`/`token`/`password`.
*Fix:* load from environment or a secret manager.

**PLB-SEC-005 — LLM-controlled SQL / query injection**
Blocker / High | CWE-89
*Detection:* taint — LLM output / untrusted input reaches a raw SQL string / query execution.
*Fix:* parameterized queries only.

**PLB-SEC-006 — LLM output rendered as HTML/markdown without sanitization**
Critical / High | OWASP LLM02 (XSS)
*Detection:* taint — LLM output reaches an HTML render/template sink with no escaping/sanitizing step.
*Fix:* sanitize or escape before rendering.

**PLB-SEC-007 — SSRF via tool/LLM-controlled URL**
Critical / High | CWE-918
*Detection:* taint — LLM output / tool argument reaches an outbound HTTP call as the URL.
*Fix:* allow-list destination hosts; block internal/metadata IP ranges.

### Category 12 — Data Privacy & Governance (`GOV`) — PILLAR: Security

**PLB-GOV-001 — PII flows into a prompt without redaction**
Critical / Medium | NIST AI RMF
*Detection:* taint — a value from a known-PII source (fields named email/phone/ssn/aadhaar, or a PII-typed source) reaches a prompt with no redaction step.
*Fix:* redact or tokenize PII before sending to a model provider.

**PLB-GOV-002 — Full prompts/responses logged at info/debug**
Major / Medium
*Detection:* a logging call whose argument includes full prompt or response content.
*Fix:* log metadata and IDs, not raw content.

### Category 13 — Model Context Protocol (`MCP`) — PILLAR: Security

New category (ADR-0018) covering MCP server/client defects. The statically-detectable MCP surface is mostly security-pillar; carried as a topical hook, not a reliability headline. Runtime-only MCP failures (tool-poisoning, rug-pull, confused-deputy OAuth) are explicitly out of scope — they are AgentGuard's domain.

**PLB-MCP-001 — Remote MCP server with no authentication**
Critical / Medium | OWASP ASI03 / MCP07 / LLM06 · CWE-306
A FastMCP server on a remote transport (`streamable-http`/`sse`) with no `auth=`/`token_verifier=` exposes every tool to anyone on the network.
*Detection:* MCP SDK imported; `FastMCP(...)` constructed with no auth kwarg; a remote transport run that is not bound to loopback. (Sanctioned AST rule — no dataflow.)
*Fix:* configure `auth=`/`token_verifier=`, or bind to `127.0.0.1` for local-only use.
*(Medium/advisory — auth can also come from ASGI middleware/a proxy this file-local view can't see.)*

**PLB-MCP-003 — Over-broad / wildcard MCP OAuth scopes**
Major / Medium | OWASP ASI03 / MCP02 / LLM06 · CWE-250
A wildcard scope (`*`, `admin:*`, `full-access`) in the server's auth config turns one stolen token into total blast radius.
*Detection:* `required_scopes=/scopes_supported=/scopes=` list literals whose string elements are wildcard/omnibus. (Pattern rule — no dataflow applies to a static scope list.)
*Fix:* request the minimal, fully-qualified scopes a caller needs.
*(Medium/advisory.)*

---

## 7. Rule count summary

| Category | Pillar | v1 rules | High-confidence |
|---|---|---|---|
| RES Resilience | Reliability | 10 | 5 |
| AGT Agent Control Flow | Architecture | 8 | 3 |
| MDL Model Lifecycle | Reliability | 8 | 2 |
| OUT Output Validation | Reliability | 4 | 2 |
| TOOL Tool Calling | Architecture | 4 | 2 |
| RAG Knowledge Architecture | Architecture | 4 | 0 |
| PRM Prompt Management | Architecture | 3 | 1 |
| EVAL Verification Harness | Harness | 4 | 1 |
| OBS Observability | Harness | 3 | 1 |
| COST Cost Efficiency | Reliability | 2 | 1 |
| SEC Security | Security | 7 | 7 |
| GOV Privacy/Governance | Security | 2 | 0 |
| MCP Model Context Protocol | Security | 2 | 0 |
| **Total** | | **61** | **25** |

**Pillar distribution of the launch set:** Reliability 20, Architecture & Agentic Maturity 18, Harness Engineering 7, Security 9. Compare to the old security-led catalog (Security was 14 of ~40). **The center of gravity has moved decisively off the crowded security space and onto reliability + architecture + harness — exactly the defensible wedge.**

**Cut to ~40 for actual launch** by deferring the Low-confidence rules (RES-009, AGT-007, MDL-005, RAG-003, EVAL-004, OBS-003) and the thinnest RAG/PRM/GOV rules to v1.1, unless design partners pull them forward. Lead every demo and every README with the **25 High-confidence rules** and with the Reliability pillar.

---

## 8. Build sequence

1. Taint engine + Python AST layer + one framework adapter (raw OpenAI/Anthropic SDK).
2. **The Reliability core first** — RES High-confidence rules + OUT + COST-001. This alone is a credible, demoable "will it survive production" linter and it is the differentiated wedge.
3. CLI + SARIF + JSON reporters + Quality Gate. Now it runs in CI.
4. LangChain/LangGraph adapter, then CrewAI adapter, + the AGT/TOOL rules that depend on them.
5. EVAL + OBS categories — the harness-engineering pillar.
6. SEC + GOV — security, covered competently, shipped after the differentiators.
7. Scoring + four sub-scores + Readiness Score + HTML report.
8. AI-assisted fix generation (detection stays deterministic).
9. **Phase 2:** trace ingestion — the bridge to the AgentGuard runtime platform. Reliability and harness defects flagged statically get *confirmed* by runtime traces.

Note the deliberate inversion from the security-led plan: **security ships in step 6, not step 2.** The differentiated reliability/architecture/harness rules go first. Security is necessary but it is not the reason anyone chooses Plumbline over the existing scanners.

---

## 9. Standards mapping

- **OWASP Top 10 for LLM Applications (2025)** and **OWASP Top 10 for Agentic Applications (2026)** — security and agentic-risk mapping.
- **NIST AI Risk Management Framework** — governance mapping.
- **CWE** — classic injection/deserialization sinks.
- For the **Reliability and Architecture** rules there is no single external standard — that *is* the gap, and it is your opportunity. Plumbline's own rule catalog, published openly, can become the de-facto reference for "what good agentic engineering looks like." Owning the reference is a moat that pure security scanners cannot contest.

---

## 10. Open-source positioning notes

- **License:** Apache-2.0 or MIT. The rule catalog is the community asset; the AgentGuard runtime platform is the commercial product.
- **Public roadmap = the full 12-category taxonomy.** v1 ships ~40 rules; the catalog shows the rest as "help wanted," weighted toward reliability/architecture so contributors extend the *differentiated* surface, not the commodity security surface.
- **One rule = one detector file + one vulnerable/clean fixture pair.** Keep the contribution barrier low.
- **The linter is the top of the funnel.** EVAL-001 and OBS-001 literally tell a team they are flying blind — and the AgentGuard runtime platform is the answer. Design the funnel deliberately; never let the linter feel like crippled-ware. It must be genuinely the best reliability/architecture analyzer for agentic code, standalone.
- **Own the vocabulary carefully.** "Reliability and architecture analyzer for agentic systems" is the durable description. "Harness engineering" is a strong concept but emerging vocabulary — use it in depth, not as the opening line.
