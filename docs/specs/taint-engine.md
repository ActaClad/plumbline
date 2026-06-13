# Spec: Taint Engine (`core/taint.py`)

**Status:** authoritative for the taint engine's semantics and API.
**Read alongside:** ADR-0003 (representation + scope decisions), ADR-0004
(semantic tags, which supply most sources), `architecture.md` §4.

The taint engine computes, deterministically, which **taint labels** reach
which expression nodes inside a Python module, with a witness path for each.
It does not know about sinks — rules combine its answers with semantic tags
to decide what is dangerous (ADR-0003 D4).

---

## 1. Labels

```
TaintLabel = USER_INPUT | LLM_OUTPUT | TOOL_RESULT | RETRIEVED_CONTENT
           | EXTERNAL_HTTP | PII
```

A node's taint is a `frozenset[TaintLabel]` — labels are independent and
compose (a value can be both `LLM_OUTPUT` and `PII`). Adding a label is a PR
updating this spec; changing a label's meaning is an ADR.

## 2. Sources

### 2.1 From the adapter layer (primary)

| Semantic tag (ADR-0004) | What gets labeled | Label |
|---|---|---|
| `LLM_CALL` | the call's result value | `LLM_OUTPUT` |
| `RETRIEVER_CALL` | the call's result value | `RETRIEVED_CONTENT` |
| `TOOL_DEF` | the tool function's parameters (inside its body) | `TOOL_RESULT` |
| `TOOL_CALL` | the call's result value | `TOOL_RESULT` |
| `HTTP_CALL` | the response object and derived `.text/.json()/.content` | `EXTERNAL_HTTP` |
| `MEMORY_APPEND` | values read back from the memory object | inherited from what was appended |

### 2.2 Built-in registry (framework-independent)

- `input(...)` result → `USER_INPUT`.
- Parameters of recognized web handlers → `USER_INPUT`. Recognition v1:
  functions decorated with `@app.route`, `@app.get/post/...`,
  `@router.get/post/...` (Flask/FastAPI idioms), and FastAPI dependency
  parameters typed as `Request`. Unrecognized frameworks simply contribute no
  sources (under-taint; precision first).
- `requests.*`/`httpx.*` call results → `EXTERNAL_HTTP` (also tagged
  `HTTP_CALL` by the core adapter).
- Names matching the PII heuristic (`email`, `phone`, `ssn`, `aadhaar`,
  `dob`, `address` as exact identifier or suffix `_email` etc.) when read
  from a parameter or attribute → `PII`. (Heuristic; rules built on PII are
  Medium confidence at best — see rule catalog PLB-GOV-001.)

The registry lives in `core/taint.py` as data (sorted tuples), so growth is
reviewable.

## 3. Propagation semantics

Forward, flow-sensitive in statement order, path-insensitive across branches,
fixpoint per scope (ADR-0003 D1). Scopes analyzed: module scope, then each
function (incl. async, nested, lambdas, comprehension scopes); module-level
bindings visible in functions carry their final-fixpoint module taint.

Taint propagates through:

| Construct | Rule |
|---|---|
| Assignment / annotated / augmented / walrus | RHS labels → target |
| Tuple/list unpacking | union of RHS labels → every target |
| f-strings, `%`, `str.format`, `+` concat, `str.join` | union of parts |
| String/bytes method calls on a tainted receiver | result tainted |
| Container literals, comprehensions, `dict(...)` | tainted if any element tainted |
| Subscript/`.get` read from tainted container | tainted (no index sensitivity) |
| Conditional expression `a if c else b` | union of `a`, `b` |
| `await expr` | transparent |
| Known propagator calls (registry: `json.loads/dumps`, `copy.copy/deepcopy`, `list/dict/tuple/set/str` constructors, `re.sub` result, …) | union of tainted args |
| Same-module user function call | callee summary: result tainted iff any argument bound to a summary-flagged parameter is tainted (ADR-0003 D3) |
| **Any other call** | result **untainted** (deliberate under-taint) |
| Attribute access on tainted value (`x.text`) | tainted |
| Boolean ops `and`/`or` | union of operands |

Not propagated (v1 boundary, ADR-0003 D6): cross-module flows; `self.attr`
instance state; `global`/`nonlocal` writes from callees; `**kwargs` through
dynamic dispatch; `exec`/`eval` effects; closures mutating enclosing state.

**Sanitizers** clear all labels: `int()`, `float()`, `bool()`, `len()`,
comparison results, `isinstance` — i.e. conversions whose output cannot carry
the original content. There is deliberately **no** string-sanitizer list in
v1 (e.g. `html.escape` clears nothing — whether escaping suffices is
sink-specific and belongs to the rule, which can inspect the witness path).

## 4. Function summaries (same-module calls)

For every function defined in the module, compute
`summary: frozenset[int]` — the set of parameter indices whose taint reaches
the function's return value, by running the same propagation with synthetic
per-parameter labels. Summaries are computed bottom-up over the module's
call graph; cycles (recursion) start from the empty summary and iterate to
fixpoint. Calls into the function then map argument taint through the
summary. Keyword arguments map by name; `*args`/`**kwargs` at the call site
make the result `untainted` + an internal "summary imprecise" note (never a
crash).

## 5. Query API (rule-facing, public contract)

```python
class TaintView:                      # exposed as ctx.taint
    def labels(self, node: ast.AST) -> frozenset[TaintLabel]: ...
    def is_tainted(self, node: ast.AST, *labels: TaintLabel) -> bool:
        """True if node carries any of the given labels (all labels if none given)."""
    def witness(self, node: ast.AST, label: TaintLabel) -> tuple[Hop, ...]:
        """Deterministic source→node path; Hop = (line, column, description)."""
```

The witness is the first path found under sorted traversal (ADR-0003 D5) and
feeds finding messages and SARIF `codeFlows` (ADR-0006 D3).

## 6. Determinism

- Statement worklist and call-graph iteration use sorted orderings (node
  position, then name).
- All public returns are immutable (`frozenset`, tuples).
- Property test in CI: analyzing a module twice yields identical
  `labels`/`witness` for every node (part of the engine double-run test,
  ADR-0002 D3).

## 7. Performance envelope

Per-scope fixpoint is O(statements × labels) per iteration with small
constant iteration counts (label sets only grow). Target: taint adds < 50%
over parse time on the benchmark corpus. Files with **no semantic nodes and
no built-in sources are skipped entirely** — the common case in a mixed repo
costs only the source scan.

## 8. Test plan

- Unit tests per propagation row in §3's table (one minimal module each).
- Loop-carried flow test (append-in-loop feeding next-iteration prompt).
- Summary tests: simple, chained, recursive, keyword-arg mapping.
- Negative tests: each v1 boundary item produces *no* taint (documents the
  boundary as executable spec).
- Witness-path stability test.

## 9. Future work (requires ADRs)

Cross-module summaries; `self.attr` tracking; sink-specific sanitizer model;
index-sensitive containers. Several Medium rules (PLB-TOOL-002 breadth,
PLB-GOV-001) can graduate when these land — tracked in `backlog.md`.
