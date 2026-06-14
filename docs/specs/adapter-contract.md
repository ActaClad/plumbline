# Spec: Framework-Adapter Contract (`adapters/`)

**Status:** authoritative for how adapters are written and what they emit.
**Read alongside:** ADR-0004 (contract decisions), `architecture.md` §5,
`taint-engine.md` §2 (how tags become taint sources).

An adapter translates one framework's API surface (raw OpenAI/Anthropic SDK,
LangChain/LangGraph, CrewAI, …) into **normalized semantic annotations** on
AST nodes. Rules consume the annotations, never framework call signatures —
that is what makes one rule cover every supported framework.

---

## 1. The semantic tag vocabulary (v1)

Owned by core (`model.py`), closed set (ADR-0004 D1):

| Tag | Anchors to | Meaning |
|---|---|---|
| `LLM_CLIENT_CREATE` | call | construction of a client object (`OpenAI()`, `Anthropic()`, `ChatOpenAI()`) |
| `LLM_CALL` | call | a model invocation whose result is model output |
| `AGENT_CREATE` | call | construction of an agent/executor/graph |
| `AGENT_INVOKE` | call | running an agent (`.invoke/.run/.kickoff`) |
| `AGENT_LOOP` | while/for | a hand-rolled agent loop (LLM call + tool dispatch inside a loop) |
| `TOOL_DEF` | functiondef/call | a function registered as a model-callable tool |
| `TOOL_CALL` | call | direct invocation of a registered tool |
| `RETRIEVER_CALL` | call | vector-store / retriever query |
| `EMBEDDING_CALL` | call | embedding computation (records the model) |
| `PROMPT_BUILD` | expr | construction of prompt/message content |
| `MEMORY_APPEND` | call | appending to conversation/agent memory |
| `OUTPUT_PARSE` | call | parsing model output (`json.loads` on LLM output, output parsers) |
| `TRACE_INIT` | call/import | observability instrumentation setup |
| `HTTP_CALL` | call | generic outbound HTTP (emitted by the built-in core adapter) |

Adding a tag = PR updating this table + the consuming code. Renaming/removing
= ADR.

## 2. `SemanticNode` and tri-state attribute resolution

```python
@dataclass(frozen=True)
class SemanticNode:
    tag: SemanticTag
    node: ast.AST                  # anchor; position comes from here
    adapter: str                   # producing adapter's name
    attrs: Mapping[str, Resolved]  # normalized, tag-specific keys
```

`Resolved` (ADR-0004 D2) is one of:

- `Set(value)` — statically resolved constant (via `core/values.py`).
- `Absent` — provably not configured at the call **or** any reachable default
  (client construction in scope, framework default known to be "none").
- `Unknown` — present but not statically resolvable, or the configuration
  point is out of scope (client imported from another module).

**Rules must treat `Unknown` as "do not fire"** for High-confidence checks.
This is the single most important convention for precision.

### Normative attribute keys

| Tag | Required keys | Optional keys |
|---|---|---|
| `LLM_CALL` | `model`, `timeout`, `tools` | `temperature`, `max_tokens`, `max_retries`, `stream`, `messages` (node ref) |
| `LLM_CLIENT_CREATE` | `timeout`, `max_retries` | `base_url`, `provider` |
| `AGENT_CREATE`/`AGENT_INVOKE` | `max_iterations`, `max_iterations_source` | `framework`, `timeout`, `token_budget` |
| `AGENT_LOOP` | `has_iteration_cap`, `has_goal_exit` (each `Set`/`Unknown`, ADR-0012 D3) | — |
| `TOOL_DEF` | `name`, `has_schema` | `params` (node refs) |
| `RETRIEVER_CALL` | `k` | `store_type` |
| `EMBEDDING_CALL` | `model` | — |
| `TRACE_INIT` | `provider` | — |

`provider` values are normalized lowercase strings (`"openai"`,
`"anthropic"`, `"langchain"`, …).

## 3. The adapter protocol

```python
class Adapter(Protocol):
    name: str                          # "openai_sdk"
    priority: int                      # higher wins on (tag, node) conflicts
    trigger_imports: frozenset[str]    # {"openai", "anthropic"}

    def annotate(self, file_ctx: FileContext) -> Iterable[SemanticNode]: ...
```

- `FileContext` gives the adapter the wrapped AST (ADR-0009), the scope/parent
  tables, the import map, and the shared value resolver — adapters never
  re-parse and never do I/O.
- The engine runs an adapter on a file if any `trigger_imports` entry appears in
  the file's imports (module or `from` form, including aliased). **Amended by
  ADR-0016:** an adapter with `project_triggered = True` (only `openai_sdk`) also
  runs when its trigger appears *anywhere in the project*, so a centralized
  client imported cross-module is still analyzed. That adapter self-scopes its
  ambiguous tails (`messages.create`, shared with Twilio) to in-file SDK imports.
- Output is collected, then sorted by `(line, column, tag)`; duplicate
  `(tag, node)` annotations keep the highest-priority adapter's version.
  Priorities: framework adapters (langchain 20, crewai 20) > raw SDK
  (openai_sdk 10) > built-in core adapter (0, emits `HTTP_CALL` and other
  framework-independent tags).
- Determinism: no dict/set iteration into output without sorting; no
  reflection on installed packages (the *scanned code's* imports decide, not
  the scanning environment).

Adapters are registered in an explicit ordered list in
`adapters/__init__.py` (ADR-0004 D5).

## 4. Shared value resolution (`core/values.py`)

One resolver used by all adapters:

1. **Literal folding:** a keyword/positional argument that is a constant, or
   a name assigned exactly once in the enclosing scope chain to a constant,
   resolves to `Set(value)`. Multiple conflicting assignments → `Unknown`.
2. **Client linking:** for a call like `client.chat.completions.create(...)`,
   walk the receiver to its binding; if bound to an `LLM_CLIENT_CREATE` node
   in module or enclosing scope, merge client attrs as defaults (call-site
   value wins). Receiver bound elsewhere (import, attribute, parameter) →
   client-level attrs `Unknown`.
3. **Framework defaults:** the adapter declares per-API defaults (e.g. the
   OpenAI SDK's default `max_retries=2`, default timeout 600s) so `Absent`
   is only reported when the *effective* value is truly unconfigured **and**
   the framework default is the hazard. Where an SDK has a safe default, the
   attr resolves to `Set(default)` with `attrs["timeout_source"] =
   Set("sdk_default")` so rules can distinguish explicit from default
   configuration.

## 5. The `openai_sdk` adapter (v1 reference adapter)

Covers raw OpenAI **and** Anthropic SDK usage (one adapter — the shapes are
near-identical):

| Pattern (incl. async/aliased forms) | Emits |
|---|---|
| `OpenAI(...)`, `AsyncOpenAI(...)`, `Anthropic(...)`, `AsyncAnthropic(...)` | `LLM_CLIENT_CREATE` |
| `<client>.chat.completions.create(...)`, `<client>.responses.create(...)`, `<client>.messages.create(...)` | `LLM_CALL` |
| `<client>.embeddings.create(...)` | `EMBEDDING_CALL` |
| messages/list construction passed to an `LLM_CALL` | `PROMPT_BUILD` |

> **Amended by ADR-0012:** an earlier draft listed `AGENT_LOOP` here. A
> hand-rolled agent loop is framework-independent (its `LLM_CALL` may be tagged
> by any adapter), so `AGENT_LOOP` is now produced by the **derived-semantics
> pass** (§10), not by this adapter.

Resolution examples (these are fixture-backed acceptance tests):

- `OpenAI()` + `create(...)` with no timeout → `timeout: Absent`*
- `OpenAI(timeout=30)` + bare `create(...)` → `timeout: Set(30)`
- `create(..., timeout=cfg.T)` where `cfg` is imported → `timeout: Unknown`

\* Subject to §4.3: if the SDK ships a finite default timeout, the adapter
reports `Set(default)` + `timeout_source="sdk_default"`, and PLB-RES-001's
detector decides whether an SDK default satisfies it (per the rule catalog:
it does — the rule targets *unbounded* calls; the rule's spec text governs).

## 6. Testing an adapter

- Fixture programs under `tests/adapters/<name>/` exercising every row of
  the pattern table (sync, async, aliased import, client-from-another-module).
- Golden assertions on the emitted `(tag, line, attrs)` tuples — exact, not
  fuzzy.
- A negative program (plain Python, no AI imports) asserting zero annotations
  and that the adapter was gated off.
- Adapter outputs feed the same double-run determinism test as the engine.

## 7. Adding an adapter (checklist)

1. Spec PR: add the framework's pattern table to this file.
2. Implement `adapters/<name>.py` against the protocol; register it with a
   priority in `adapters/__init__.py`.
3. Fixture programs + golden tests (§6).
4. Run the full rule suite over the new adapter's fixtures — existing rules
   gain coverage; any rule that misfires on idiomatic usage of the new
   framework is a precision bug to fix **before** merge.

## 8. The `langchain` adapter (LangChain / LangGraph)

**Version assumption:** LangChain ≥ 0.1 / LangGraph ≥ 0.1. The frameworks churn
their public API hard (`initialize_agent` is deprecated in favour of LCEL /
LangGraph; class locations move between `langchain`, `langchain_core`,
`langchain_openai`, `langchain_community`). The adapter matches by the trailing
construct name and attribute tail, not by exact import path, so an aliased or
relocated import still resolves. Priority **20** (framework adapter > raw SDK).
`trigger_imports = {"langchain", "langchain_core", "langchain_openai",
"langchain_anthropic", "langchain_community", "langgraph"}`.

| Pattern (incl. aliased forms) | Emits | Notes |
|---|---|---|
| `ChatOpenAI(...)`, `ChatAnthropic(...)`, `AzureChatOpenAI(...)`, `ChatVertexAI(...)` | `LLM_CLIENT_CREATE` | `provider` normalized (`openai`/`anthropic`/…); these are also models, but in LCEL the construct is the client |
| `<model>.invoke(...)`, `.ainvoke(...)`, `.stream(...)`, `.batch(...)` on a chat model | `LLM_CALL` | `model` resolved from the client construction when linkable |
| `AgentExecutor(...)`, `initialize_agent(...)` | `AGENT_CREATE` | `max_iterations` default **15**; resolved per ADR-0012 D4 |
| `create_react_agent(...)`, `create_tool_calling_agent(...)`, `StateGraph(...).compile(...)` | `AGENT_CREATE` | LangGraph; bounded by a default `recursion_limit` (**25**) — recorded as `max_iterations = Known(25)`, `source="framework_default"` |
| `<agent>.invoke(...)`, `.ainvoke(...)`, `.run(...)`, `.stream(...)` on an agent/graph | `AGENT_INVOKE` | `max_iterations` re-read from a `config={"recursion_limit": N}` kwarg when present |
| `@tool` decorator; `Tool(...)`, `StructuredTool.from_function(...)` | `TOOL_DEF` | `has_schema` from `args_schema=` / a typed function signature (ADR-0012-adjacent; consumed by TOOL-001) |

`max_iterations` provenance follows ADR-0012 D4: bare construction →
`Known(<finite default>)` + `source="framework_default"`; explicit
`max_iterations=None` → `Known(None)` + `source="explicit"`; unresolvable →
`UNKNOWN`. Correctness depends only on a finite default *existing*, not its
exact value (the numbers above are the current defaults, stated for the reader).

## 9. The `crewai` adapter (CrewAI)

**Version assumption:** CrewAI ≥ 0.1. Priority **20**.
`trigger_imports = {"crewai", "crewai_tools"}`.

| Pattern | Emits | Notes |
|---|---|---|
| `Agent(...)` | `AGENT_CREATE` | `max_iter` is CrewAI's per-agent cap; finite framework default (**25**). Read into `max_iterations` (normalized key) per ADR-0012 D4 |
| `Crew(...)` | `AGENT_CREATE` | orchestration object; `max_iterations` taken from `max_iter`/`max_rpm` when present, else `framework_default` (an agent-bounded crew is bounded) |
| `<crew>.kickoff(...)`, `.kickoff_async(...)` | `AGENT_INVOKE` | — |
| `Task(...)` | — | not tagged in v1 (no rule consumes it yet) |
| `@tool` decorator; `BaseTool` subclass | `TOOL_DEF` | `has_schema` from `args_schema` / typed `_run` signature |

## 10. Derived semantics (`core/derive.py`, ADR-0012 D1)

After every adapter has run, the engine runs one deterministic derivation pass
over `(SourceTree, collected nodes)` to compute **cross-cutting** tags that no
single adapter can see. It is pure (no I/O, no adapter calls) and its output is
appended before indexing. v1 derives exactly one tag:

**`AGENT_LOOP`** — a `while`/`for` statement whose body (excluding nested
function/class defs) transitively contains ≥1 `LLM_CALL` (ADR-0012 D2). It
carries two independent tri-state properties (ADR-0012 D3):

- `has_iteration_cap` — `Known(True)` for `for`-over-`range`/literal or a
  counter-guarded `while`; `Known(False)` for `while True:`/`while 1:` with no
  counter; `UNKNOWN` otherwise.
- `has_goal_exit` — `Known(True)` for any `for`, any non-constant `while`, or a
  truthy-constant `while` with a reachable `break`/`return`; `Known(False)` for
  a truthy-constant `while` with none; (never `UNKNOWN` in v1).

A loop with no `LLM_CALL` inside it is never tagged — narrowing the population
is the precision mechanism. Anchor: the loop statement node.
