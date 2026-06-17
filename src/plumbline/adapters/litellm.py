"""The LiteLLM adapter (adapter-contract.md §10a).

`litellm.completion(...)` is the unified call across 100+ providers; a large
slice of real apps (babyagi among them) drive the model through LiteLLM and were
invisible to Plumbline — a recall gap found in real-repo validation.

Like the openai_sdk adapter, it resolves config **at the call level only and
claims no framework defaults**: a bare `completion(...)` leaves timeout/retries
ABSENT (so RES-001/002 stay silent on defaults, matching the OpenAI precedent),
while an explicit `timeout=None` or `num_retries=0` fires. LiteLLM's retry knob is
`num_retries`; it is read into the normalized `max_retries` key. Matching is by
the imported name via `resolve_qualified` (alias-proof), so it stays per-file
(`project_triggered=False`) — `completion` is too generic to widen project-wide.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable

from ..core.ast_layer import Scope, SourceTree
from ..core.values import resolve_call_keyword, resolve_qualified
from ..model import Resolved, SemanticNode, SemanticTag

_COMPLETION: frozenset[str] = frozenset(
    {"completion", "acompletion", "text_completion", "atext_completion"}
)
_EMBEDDING: frozenset[str] = frozenset({"embedding", "aembedding"})


class LiteLLMAdapter:
    name = "litellm"
    priority = 15
    trigger_imports = frozenset({"litellm"})
    project_triggered = False

    def annotate(self, ctx: SourceTree) -> Iterable[SemanticNode]:
        out: list[SemanticNode] = []
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.Call):
                continue
            qualified = resolve_qualified(ctx, node.func)
            if qualified is None or qualified[0] != "litellm":
                continue
            fn = qualified[1]
            scope = ctx.scope_of(node)
            if fn in _COMPLETION:
                out.append(
                    SemanticNode(
                        SemanticTag.LLM_CALL, node, self.name, self._attrs(ctx, scope, node)
                    )
                )
            elif fn in _EMBEDDING:
                model = resolve_call_keyword(ctx, scope, node, "model")
                out.append(
                    SemanticNode(SemanticTag.EMBEDDING_CALL, node, self.name, {"model": model})
                )
        return out

    def _attrs(self, ctx: SourceTree, scope: Scope, call: ast.Call) -> dict[str, Resolved]:
        return {
            "model": resolve_call_keyword(ctx, scope, call, "model"),
            "timeout": resolve_call_keyword(ctx, scope, call, "timeout"),
            "max_tokens": resolve_call_keyword(ctx, scope, call, "max_tokens"),
            "tools": resolve_call_keyword(ctx, scope, call, "tools"),
            # LiteLLM's retry knob is `num_retries` -> normalized `max_retries`.
            "max_retries": resolve_call_keyword(ctx, scope, call, "num_retries"),
        }
