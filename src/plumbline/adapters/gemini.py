"""The Google Gemini adapter (adapter-contract.md §9b).

Covers Google's current `google-genai` SDK — `from google import genai` /
`genai.Client(...)` / `client.models.generate_content(...)` and its async
`client.aio.models.generate_content(...)` form, plus the streaming and Live
variants — and the legacy `google.generativeai` SDK
(`genai.GenerativeModel(...).generate_content(...)`). Before this adapter, an
entire Gemini app was invisible to Plumbline: a real production voice-agent
scanned to `0 findings / Readiness N/A` because every LLM call went through an
unrecognized SDK.

Precision note (constitution §1.4). Gemini nests its generation config inside a
`config=GenerateContentConfig(...)` object and the client timeout inside
`http_options`, so — unlike the top-level kwargs of the OpenAI/LiteLLM SDKs —
those values are not resolvable at the call site in v1. This adapter therefore
resolves only what it can prove (`model`, `provider`) and leaves
`timeout`/`max_tokens`/`tools`/`temperature`/`max_retries` UNKNOWN, so the
High-confidence RES/COST/MDL rules stay silent (do-not-fire on UNKNOWN,
adapter-contract §2) instead of false-positiving. What it delivers is real: the
app is no longer invisible (Readiness is scored; the harness OBS/EVAL rules
fire), and `generate_content` output seeds taint for OUT-001. Resolving the
nested `GenerateContentConfig` is a tracked follow-up (docs/backlog.md).
"""

from __future__ import annotations

import ast
from collections.abc import Iterable

from ..core.ast_layer import SourceTree
from ..core.values import resolve_call_keyword
from ..model import UNKNOWN, Known, Resolved, SemanticNode, SemanticTag

# Import identities of the Gemini module namespace, as recorded by the import map
# (ast_layer `_record_bindings`):
#   `from google import genai`   -> ImportedName(module="google", qualname="genai")
#   `import google.genai [as g]` -> ImportedName(module="google.genai", qualname="")
_NEW_MODULE_IDS = frozenset({("google", "genai"), ("google.genai", "")})
_LEGACY_MODULE_IDS = frozenset({("google", "generativeai"), ("google.generativeai", "")})

# Method-call attribute tails on a client/model instance (new SDK). Matched by
# suffix so the sync (`client.models.…`) and async (`client.aio.models.…`) forms
# both resolve. generate_content (+ its streaming form) and the Live session are
# model invocations; embed_content is an embedding.
_CALL_TAILS: tuple[tuple[str, ...], ...] = (
    ("models", "generate_content"),
    ("aio", "models", "generate_content"),
    ("models", "generate_content_stream"),
    ("aio", "models", "generate_content_stream"),
    ("live", "connect"),
    ("aio", "live", "connect"),
)
_EMBED_TAILS: tuple[tuple[str, ...], ...] = (
    ("models", "embed_content"),
    ("aio", "models", "embed_content"),
)
# Legacy `model.generate_content(...)` is a bare tail (the model instance carries
# no distinguishing chain), so it is only honored when a legacy import is present
# in the file — otherwise it is too generic to be safe.
_LEGACY_CALL_NAMES = frozenset({"generate_content", "generate_content_async"})
_LEGACY_EMBED_NAMES = frozenset({"embed_content"})


class GeminiAdapter:
    name = "gemini"
    priority = 15
    trigger_imports = frozenset({"google"})
    project_triggered = False

    def annotate(self, ctx: SourceTree) -> Iterable[SemanticNode]:
        legacy_in_file = _legacy_imported(ctx)
        out: list[SemanticNode] = []
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.Call):
                continue
            sn = self._match(ctx, node, legacy_in_file)
            if sn is not None:
                out.append(sn)
        return out

    def _match(self, ctx: SourceTree, call: ast.Call, legacy_in_file: bool) -> SemanticNode | None:
        if _ctor_kind(ctx, call.func) is not None:
            return self._client_create(call)
        tail = _attr_tail(call.func)
        if _suffix_in(tail, _CALL_TAILS):
            return self._llm_call(ctx, call)
        if _suffix_in(tail, _EMBED_TAILS):
            return self._embedding_call(ctx, call)
        # Legacy bare tails only when a legacy import is present (the new-SDK
        # chained forms already matched above, so this cannot double-tag them).
        if legacy_in_file and tail:
            if tail[-1] in _LEGACY_CALL_NAMES:
                return self._llm_call(ctx, call)
            if tail[-1] in _LEGACY_EMBED_NAMES:
                return self._embedding_call(ctx, call)
        return None

    def _client_create(self, call: ast.Call) -> SemanticNode:
        # timeout/max_retries live inside `http_options=` — not resolved in v1.
        attrs: dict[str, Resolved] = {
            "provider": Known("google"),
            "timeout": UNKNOWN,
            "max_retries": UNKNOWN,
        }
        return SemanticNode(SemanticTag.LLM_CLIENT_CREATE, call, self.name, attrs)

    def _llm_call(self, ctx: SourceTree, call: ast.Call) -> SemanticNode:
        scope = ctx.scope_of(call)
        # `model` is a top-level kwarg on generate_content / live.connect; the rest
        # are nested in `config=GenerateContentConfig(...)` -> honest UNKNOWN.
        attrs: dict[str, Resolved] = {
            "provider": Known("google"),
            "model": resolve_call_keyword(ctx, scope, call, "model"),
            "timeout": UNKNOWN,
            "max_tokens": UNKNOWN,
            "max_retries": UNKNOWN,
            "tools": UNKNOWN,
            "temperature": UNKNOWN,
        }
        return SemanticNode(SemanticTag.LLM_CALL, call, self.name, attrs)

    def _embedding_call(self, ctx: SourceTree, call: ast.Call) -> SemanticNode:
        scope = ctx.scope_of(call)
        attrs: dict[str, Resolved] = {"model": resolve_call_keyword(ctx, scope, call, "model")}
        return SemanticNode(SemanticTag.EMBEDDING_CALL, call, self.name, attrs)


def _module_id(ctx: SourceTree, name_node: ast.expr) -> tuple[str, str] | None:
    """The (module, qualname) the receiver Name was imported as, or None."""
    if not isinstance(name_node, ast.Name):
        return None
    info = ctx.imports.get(name_node.id)
    if info is None:
        return None
    return (info.module, info.qualname)


def _ctor_kind(ctx: SourceTree, func: ast.expr) -> str | None:
    """ "new"/"legacy" if `func` is a Gemini client/model constructor, else None."""
    # Attribute form: `genai.Client(...)` / `genai.GenerativeModel(...)`.
    if isinstance(func, ast.Attribute):
        mod_id = _module_id(ctx, func.value)
        if mod_id in _NEW_MODULE_IDS and func.attr == "Client":
            return "new"
        if mod_id in _LEGACY_MODULE_IDS and func.attr == "GenerativeModel":
            return "legacy"
    # Name form: `from google.genai import Client; Client(...)`.
    if isinstance(func, ast.Name):
        info = ctx.imports.get(func.id)
        if info is not None:
            if (info.module, info.qualname) == ("google.genai", "Client"):
                return "new"
            if (info.module, info.qualname) == ("google.generativeai", "GenerativeModel"):
                return "legacy"
    return None


def _legacy_imported(ctx: SourceTree) -> bool:
    for info in ctx.imports.values():
        if (info.module, info.qualname) in _LEGACY_MODULE_IDS:
            return True
        if info.module == "google.generativeai" or info.module.startswith("google.generativeai."):
            return True
    return False


def _attr_tail(func: ast.expr) -> list[str]:
    names: list[str] = []
    cur: ast.expr = func
    while isinstance(cur, ast.Attribute):
        names.append(cur.attr)
        cur = cur.value
    names.reverse()
    return names


def _suffix_in(tail: list[str], options: tuple[tuple[str, ...], ...]) -> bool:
    return any(len(tail) >= len(opt) and tuple(tail[-len(opt) :]) == opt for opt in options)
