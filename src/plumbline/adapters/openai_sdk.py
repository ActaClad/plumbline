"""The raw OpenAI/Anthropic SDK adapter (adapter-contract.md §5).

One adapter covers both SDKs — their call shapes are near-identical. It emits
LLM_CLIENT_CREATE, LLM_CALL, and EMBEDDING_CALL, resolving timeout/max_retries
by merging call-level config over client-level config (call wins), then falling
back to the SDK's framework default with provenance (ADR-0004 D3,
adapter-contract §4.3). Other call-level params (model, temperature, …) are
resolved at the call site only.
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

# (module, qualname) of a client constructor -> normalized provider.
_CLIENT_CTORS: dict[tuple[str, str], str] = {
    ("openai", "OpenAI"): "openai",
    ("openai", "AsyncOpenAI"): "openai",
    ("anthropic", "Anthropic"): "anthropic",
    ("anthropic", "AsyncAnthropic"): "anthropic",
}

# Per-provider safe defaults. Both SDKs ship a finite default timeout and
# retries, so an unconfigured call is NOT unbounded (detailed-design §9.4).
_PROVIDER_DEFAULTS: dict[str, dict[str, object]] = {
    "openai": {"timeout": 600.0, "max_retries": 2},
    "anthropic": {"timeout": 600.0, "max_retries": 2},
}

# Trailing attribute paths that denote a model call. The OpenAI-unique shapes are
# safe to tag project-wide (ADR-0016 D2); `messages.create` is ALSO Twilio's SMS
# API, so it is only tagged when openai/anthropic is imported in the same file.
_UNAMBIGUOUS_CALL_TAILS: tuple[tuple[str, ...], ...] = (
    ("chat", "completions", "create"),
    ("responses", "create"),
)
_AMBIGUOUS_CALL_TAILS: tuple[tuple[str, ...], ...] = (("messages", "create"),)
_EMBED_TAIL: tuple[str, ...] = ("embeddings", "create")

_CALL_LEVEL_PARAMS = ("model", "temperature", "max_tokens", "tools", "stream")
_MERGED_PARAMS = ("timeout", "max_retries")


class OpenAISDKAdapter:
    name = "openai_sdk"
    priority = 10
    trigger_imports = frozenset({"openai", "anthropic"})
    project_triggered = True  # catch centralized clients used cross-module (ADR-0016)

    def annotate(self, ctx: SourceTree) -> Iterable[SemanticNode]:
        # `messages.create` is ambiguous with Twilio, so it counts as a model call
        # only when the SDK is imported in THIS file (ADR-0016 D2).
        sdk_in_file = bool(ctx.imported_roots & self.trigger_imports)
        out: list[SemanticNode] = []
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.Call):
                continue
            qualified = resolve_qualified(ctx, node.func)
            if qualified is not None and qualified in _CLIENT_CTORS:
                out.append(self._client_create(ctx, node, _CLIENT_CTORS[qualified]))
                continue
            tail = _attr_tail(node.func)
            # `<client>.beta.threads.messages.create(...)` is the Assistants API
            # ADDING a message to a thread — NOT a generation. Exclude it (it ends
            # in messages.create but `threads` is in the chain).
            is_thread_message = "threads" in tail
            if _matches(tail, _UNAMBIGUOUS_CALL_TAILS) or (
                sdk_in_file and _matches(tail, _AMBIGUOUS_CALL_TAILS) and not is_thread_message
            ):
                out.append(self._llm_call(ctx, node))
            elif tail[-len(_EMBED_TAIL) :] == list(_EMBED_TAIL):
                out.append(self._embedding_call(ctx, node))
        return out

    def _client_create(self, ctx: SourceTree, call: ast.Call, provider: str) -> SemanticNode:
        scope = ctx.scope_of(call)
        attrs: dict[str, Resolved] = {"provider": Known(provider)}
        for name in _MERGED_PARAMS:
            attrs[name] = resolve_call_keyword(ctx, scope, call, name)
        return SemanticNode(SemanticTag.LLM_CLIENT_CREATE, call, self.name, attrs)

    def _llm_call(self, ctx: SourceTree, call: ast.Call) -> SemanticNode:
        scope = ctx.scope_of(call)
        client_create, provider = self._linked_client(ctx, scope, call)
        attrs: dict[str, Resolved] = {"provider": Known(provider) if provider else UNKNOWN}
        for name in _CALL_LEVEL_PARAMS:
            attrs[name] = resolve_call_keyword(ctx, scope, call, name)
        for name in _MERGED_PARAMS:
            value, source = self._merge(ctx, scope, call, client_create, provider, name)
            attrs[name] = value
            if source is not None:
                attrs[f"{name}_source"] = Known(source)
        return SemanticNode(SemanticTag.LLM_CALL, call, self.name, attrs)

    def _embedding_call(self, ctx: SourceTree, call: ast.Call) -> SemanticNode:
        scope = ctx.scope_of(call)
        attrs: dict[str, Resolved] = {"model": resolve_call_keyword(ctx, scope, call, "model")}
        return SemanticNode(SemanticTag.EMBEDDING_CALL, call, self.name, attrs)

    def _linked_client(
        self, ctx: SourceTree, scope: Scope, call: ast.Call
    ) -> tuple[ast.Call | None, str | None]:
        root = root_name_of(call.func)
        if root is None:
            return None, None
        rhs = single_assignment(ctx, scope, root)
        if isinstance(rhs, ast.Call):
            qualified = resolve_qualified(ctx, rhs.func)
            if qualified is not None and qualified in _CLIENT_CTORS:
                return rhs, _CLIENT_CTORS[qualified]
        return None, None

    def _merge(
        self,
        ctx: SourceTree,
        scope: Scope,
        call: ast.Call,
        client_create: ast.Call | None,
        provider: str | None,
        name: str,
    ) -> tuple[Resolved, str | None]:
        """Resolve `name` with precedence: call > client-create > SDK default.

        Returns (effective value, provenance) where provenance is
        "explicit" | "client" | "sdk_default" | None.
        """
        at_call = resolve_call_keyword(ctx, scope, call, name)
        if at_call is not ABSENT:
            return at_call, "explicit"
        if client_create is not None:
            at_client = resolve_call_keyword(ctx, ctx.scope_of(client_create), client_create, name)
            if at_client is not ABSENT:
                return at_client, "client"
        if provider is not None and name in _PROVIDER_DEFAULTS[provider]:
            return Known(_PROVIDER_DEFAULTS[provider][name]), "sdk_default"
        # Unconfigured and no known default (e.g. client not resolvable):
        # honest UNKNOWN, not ABSENT — we cannot prove the call is unbounded.
        return UNKNOWN, None


def _attr_tail(func: ast.expr) -> list[str]:
    names: list[str] = []
    cur: ast.expr = func
    while isinstance(cur, ast.Attribute):
        names.append(cur.attr)
        cur = cur.value
    names.reverse()
    return names


def _matches(tail: list[str], options: tuple[tuple[str, ...], ...]) -> bool:
    return any(tail[-len(opt) :] == list(opt) for opt in options if len(tail) >= len(opt))
