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
| `AGENT_CREATE`/`AGENT_INVOKE` | `max_iterations` | `timeout`, `token_budget` |
| `AGENT_LOOP` | `bounded` (`Set(True/False)`/`Unknown`) | `bound_expr` (node ref) |
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
- The engine runs an adapter on a file only if any `trigger_imports` entry
  appears in the file's imports (module or `from` form, including aliased).
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
| a `while`/`for` whose body contains an `LLM_CALL` and dispatch on tool/function-call results | `AGENT_LOOP` |

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
