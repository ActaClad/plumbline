"""The LangChain / LangGraph adapter (adapter-contract.md §8).

Translates LangChain and LangGraph constructs into the normalized semantic
vocabulary so the reliability/agent rules cover them unchanged. Matching is by
the imported construct *name* (alias- and module-path-proof via
`resolve_qualified`), never by exact import path — these frameworks relocate
classes between `langchain`, `langchain_core`, `langchain_openai`, … across
versions (§8 version assumption).

`max_iterations` is resolved against the framework's finite default (ADR-0012
D4): a bare `AgentExecutor(...)` is bounded (default 15), so AGT-001 fires only
on an explicit `max_iterations=None`, never on bare construction. Correctness
rests only on a finite default *existing*, not its exact value.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable

from ..core.ast_layer import Scope, SourceTree
from ..core.values import (
    resolve_call_keyword,
    resolve_qualified,
    root_name_of,
    single_assignment,
)
from ..model import ABSENT, UNKNOWN, Known, Resolved, SemanticNode, SemanticTag

# Chat-model constructors -> normalized provider. These are LLM_CLIENT_CREATE in
# LCEL (the construct is both the client and the model handle).
_CHAT_MODELS: dict[str, str] = {
    "ChatOpenAI": "openai",
    "AzureChatOpenAI": "openai",
    "ChatAnthropic": "anthropic",
    "ChatVertexAI": "google",
    "ChatGoogleGenerativeAI": "google",
    "ChatBedrock": "aws",
    "ChatBedrockConverse": "aws",
    "ChatMistralAI": "mistral",
    "ChatGroq": "groq",
    "ChatCohere": "cohere",
    "ChatFireworks": "fireworks",
    "ChatOllama": "ollama",
}

# Agent constructors that take a `max_iterations` cap (finite default 15).
_AGENT_ITER_CTORS: frozenset[str] = frozenset({"AgentExecutor", "initialize_agent"})
# LangGraph prebuilt/compiled agents: bounded by a default recursion_limit (25);
# they have no construct-time `max_iterations` knob, so they are always bounded.
_AGENT_GRAPH_CTORS: frozenset[str] = frozenset(
    {"create_react_agent", "create_tool_calling_agent", "create_openai_tools_agent"}
)
_ITER_DEFAULT = 15
_GRAPH_DEFAULT = 25

_INVOKE_METHODS: frozenset[str] = frozenset({"invoke", "ainvoke", "stream", "astream", "batch"})


class LangChainAdapter:
    name = "langchain"
    priority = 20
    project_triggered = False  # name-based matching; stays per-file (ADR-0016 D1)
    trigger_imports = frozenset(
        {
            "langchain",
            "langchain_core",
            "langchain_openai",
            "langchain_anthropic",
            "langchain_community",
            "langchain_google_genai",
            "langgraph",
        }
    )

    def annotate(self, ctx: SourceTree) -> Iterable[SemanticNode]:
        out: list[SemanticNode] = []
        for node in ast.walk(ctx.tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                tool = self._tool_from_decorated_fn(ctx, node)
                if tool is not None:
                    out.append(tool)
                continue
            if not isinstance(node, ast.Call):
                continue
            sn = self._from_call(ctx, node)
            if sn is not None:
                out.append(sn)
        return out

    # -- constructors / calls --------------------------------------------------

    def _from_call(self, ctx: SourceTree, call: ast.Call) -> SemanticNode | None:
        scope = ctx.scope_of(call)
        qn = resolve_qualified(ctx, call.func)
        ctor = qn[1] if qn is not None else None

        if ctor in _CHAT_MODELS:
            return self._client_create(ctx, scope, call, _CHAT_MODELS[ctor])
        if ctor in _AGENT_ITER_CTORS:
            return self._agent_create(ctx, scope, call, _ITER_DEFAULT)
        if ctor in _AGENT_GRAPH_CTORS:
            return self._agent_create(ctx, scope, call, _GRAPH_DEFAULT)
        if ctor in ("Tool", "StructuredTool"):
            return self._tool_from_ctor(call)

        # Method-style calls need the receiver, not resolve_qualified.
        func = call.func
        if isinstance(func, ast.Attribute):
            # `StructuredTool.from_function(...)` / `Tool.from_function(...)`.
            if func.attr == "from_function" and _name_in(func.value, ("StructuredTool", "Tool")):
                return self._tool_from_ctor(call)
            if func.attr == "compile" and self._links_to_ctor(ctx, scope, call, {"StateGraph"}):
                return self._agent_create(ctx, scope, call, _GRAPH_DEFAULT)
            if func.attr in _INVOKE_METHODS:
                return self._invoke(ctx, scope, call)
        return None

    def _client_create(
        self, ctx: SourceTree, scope: Scope, call: ast.Call, provider: str
    ) -> SemanticNode:
        model = resolve_call_keyword(ctx, scope, call, "model")
        if model is ABSENT:
            model = resolve_call_keyword(ctx, scope, call, "model_name")  # older arg name
        attrs: dict[str, Resolved] = {
            "provider": Known(provider),
            "model": model,
            "timeout": resolve_call_keyword(ctx, scope, call, "timeout"),
            "max_retries": resolve_call_keyword(ctx, scope, call, "max_retries"),
        }
        return SemanticNode(SemanticTag.LLM_CLIENT_CREATE, call, self.name, attrs)

    def _agent_create(
        self, ctx: SourceTree, scope: Scope, call: ast.Call, default: int
    ) -> SemanticNode:
        value, source = _resolve_capped(ctx, scope, call, "max_iterations", default)
        attrs: dict[str, Resolved] = {
            "framework": Known("langchain"),
            "max_iterations": value,
            "max_iterations_source": Known(source),
        }
        return SemanticNode(SemanticTag.AGENT_CREATE, call, self.name, attrs)

    def _invoke(self, ctx: SourceTree, scope: Scope, call: ast.Call) -> SemanticNode | None:
        client = self._receiver_ctor(ctx, scope, call)
        kind = self._linked_kind(ctx, scope, call)
        if kind == "model":
            return SemanticNode(
                SemanticTag.LLM_CALL,
                call,
                self.name,
                self._llm_call_attrs(ctx, scope, call, client),
            )
        if kind == "agent":
            return SemanticNode(SemanticTag.AGENT_INVOKE, call, self.name, {})
        return None  # unlinkable receiver -> under-tag (precision over recall).

    def _llm_call_attrs(
        self, ctx: SourceTree, scope: Scope, call: ast.Call, client: ast.Call | None
    ) -> dict[str, Resolved]:
        """Merge call-level over client-level config (call wins). In LangChain,
        `max_tokens`/`timeout`/`model` are almost always set on the model
        construction, not the `.invoke()` call — so resolving the call alone
        would make COST-001/RES-001 misfire on idiomatic code (adapter-contract
        §7.4). Genuine ABSENT (uncapped at BOTH layers) is reported; an
        unlinkable client yields UNKNOWN, never a false ABSENT."""
        return {
            "model": self._merged(ctx, scope, call, client, "model", "model_name"),
            "timeout": self._merged(ctx, scope, call, client, "timeout", "request_timeout"),
            "max_tokens": self._merged(ctx, scope, call, client, "max_tokens"),
            "tools": resolve_call_keyword(ctx, scope, call, "tools"),
        }

    def _merged(
        self,
        ctx: SourceTree,
        scope: Scope,
        call: ast.Call,
        client: ast.Call | None,
        *names: str,
    ) -> Resolved:
        for name in names:
            at_call = resolve_call_keyword(ctx, scope, call, name)
            if at_call is not ABSENT:
                return at_call
        if client is None:
            return UNKNOWN  # cannot see the model construction -> cannot prove absence
        cscope = ctx.scope_of(client)
        for name in names:
            at_client = resolve_call_keyword(ctx, cscope, client, name)
            if at_client is not ABSENT:
                return at_client
        return ABSENT  # genuinely unset at call AND client construction

    # -- tools -----------------------------------------------------------------

    def _tool_from_decorated_fn(
        self, ctx: SourceTree, fn: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> SemanticNode | None:
        for dec in fn.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            name = (
                target.attr
                if isinstance(target, ast.Attribute)
                else (target.id if isinstance(target, ast.Name) else None)
            )
            if name != "tool":
                continue
            # `@tool(args_schema=...)` declares a schema; otherwise infer from hints.
            declared = isinstance(dec, ast.Call) and any(
                k.arg == "args_schema" for k in dec.keywords
            )
            has_schema = Known(True) if declared else Known(_all_params_annotated(fn))
            return SemanticNode(
                SemanticTag.TOOL_DEF,
                fn,
                self.name,
                {"name": Known(fn.name), "has_schema": has_schema},
            )
        return None

    def _tool_from_ctor(self, call: ast.Call) -> SemanticNode:
        declared = any(k.arg == "args_schema" for k in call.keywords)
        return SemanticNode(
            SemanticTag.TOOL_DEF,
            call,
            self.name,
            {"name": UNKNOWN, "has_schema": Known(declared)},
        )

    # -- receiver linking ------------------------------------------------------

    def _linked_kind(self, ctx: SourceTree, scope: Scope, call: ast.Call) -> str | None:
        rhs = self._receiver_ctor(ctx, scope, call)
        if rhs is None:
            return None
        qn = resolve_qualified(ctx, rhs.func)
        ctor = qn[1] if qn is not None else None
        if ctor in _CHAT_MODELS:
            return "model"
        if ctor in _AGENT_ITER_CTORS or ctor in _AGENT_GRAPH_CTORS:
            return "agent"
        return None

    def _links_to_ctor(
        self, ctx: SourceTree, scope: Scope, call: ast.Call, ctors: set[str]
    ) -> bool:
        rhs = self._receiver_ctor(ctx, scope, call)
        if rhs is None:
            return False
        qn = resolve_qualified(ctx, rhs.func)
        return qn is not None and qn[1] in ctors

    @staticmethod
    def _receiver_ctor(ctx: SourceTree, scope: Scope, call: ast.Call) -> ast.Call | None:
        root = root_name_of(call.func)
        if root is None:
            return None
        rhs = single_assignment(ctx, scope, root)
        return rhs if isinstance(rhs, ast.Call) else None


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _resolve_capped(
    ctx: SourceTree, scope: Scope, call: ast.Call, name: str, default: int
) -> tuple[Resolved, str]:
    """Resolve a cap keyword with framework-default provenance (ADR-0012 D4)."""
    at_call = resolve_call_keyword(ctx, scope, call, name)
    if at_call is ABSENT:
        return Known(default), "framework_default"
    if at_call is UNKNOWN:
        return UNKNOWN, "unknown"
    return at_call, "explicit"


def _name_in(node: ast.expr, names: tuple[str, ...]) -> bool:
    return isinstance(node, ast.Name) and node.id in names


def _all_params_annotated(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    params = [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]
    real = [a for a in params if a.arg not in ("self", "cls")]
    return bool(real) and all(a.annotation is not None for a in real)
