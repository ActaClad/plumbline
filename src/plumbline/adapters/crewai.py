"""The CrewAI adapter (adapter-contract.md §9).

Translates CrewAI's `Agent`/`Crew`/`@tool` surface into the normalized semantic
vocabulary. CrewAI's per-agent iteration cap is spelled `max_iter` (finite
default 25); it is read into the normalized `max_iterations` key so the SAME
AGT-001 detector fires across CrewAI, LangChain, and hand-rolled loops.

Per ADR-0012 D4, bare construction resolves to the finite framework default
(never ABSENT), so AGT-001 fires only on an explicit `max_iter=None` — not on
idiomatic bare agents. Correctness rests on a finite default existing, not its
exact value (§9 version assumption).
"""

from __future__ import annotations

import ast
from collections.abc import Iterable

from ..core.ast_layer import Scope, SourceTree
from ..core.values import resolve_call_keyword, resolve_qualified
from ..model import ABSENT, UNKNOWN, Known, Resolved, SemanticNode, SemanticTag

_MAX_ITER_DEFAULT = 25  # CrewAI Agent.max_iter default
_INVOKE_METHODS: frozenset[str] = frozenset({"kickoff", "kickoff_async"})


class CrewAIAdapter:
    name = "crewai"
    priority = 20
    project_triggered = False  # name-based matching; stays per-file (ADR-0016 D1)
    trigger_imports = frozenset({"crewai", "crewai_tools"})

    def annotate(self, ctx: SourceTree) -> Iterable[SemanticNode]:
        out: list[SemanticNode] = []
        for node in ast.walk(ctx.tree):
            if isinstance(node, ast.ClassDef):
                tool = self._tool_from_class(node)
                if tool is not None:
                    out.append(tool)
                continue
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                tool = self._tool_from_decorated_fn(node)
                if tool is not None:
                    out.append(tool)
                continue
            if isinstance(node, ast.Call):
                sn = self._from_call(ctx, node)
                if sn is not None:
                    out.append(sn)
        return out

    def _from_call(self, ctx: SourceTree, call: ast.Call) -> SemanticNode | None:
        scope = ctx.scope_of(call)
        qn = resolve_qualified(ctx, call.func)
        ctor = qn[1] if qn is not None else None

        if ctor in ("Agent", "Crew"):
            return self._agent_create(ctx, scope, call)

        func = call.func
        if isinstance(func, ast.Attribute) and func.attr in _INVOKE_METHODS:
            return SemanticNode(SemanticTag.AGENT_INVOKE, call, self.name, {})
        return None

    def _agent_create(self, ctx: SourceTree, scope: Scope, call: ast.Call) -> SemanticNode:
        # `max_iter` is CrewAI's cap; fall back to the framework default.
        value, source = _resolve_cap(ctx, scope, call)
        attrs: dict[str, Resolved] = {
            "framework": Known("crewai"),
            "max_iterations": value,
            "max_iterations_source": Known(source),
        }
        return SemanticNode(SemanticTag.AGENT_CREATE, call, self.name, attrs)

    def _tool_from_decorated_fn(
        self, fn: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> SemanticNode | None:
        for dec in fn.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            name = (
                target.attr
                if isinstance(target, ast.Attribute)
                else (target.id if isinstance(target, ast.Name) else None)
            )
            if name == "tool":
                return SemanticNode(
                    SemanticTag.TOOL_DEF,
                    fn,
                    self.name,
                    {"name": Known(fn.name), "has_schema": Known(_all_params_annotated(fn))},
                )
        return None

    def _tool_from_class(self, cls: ast.ClassDef) -> SemanticNode | None:
        # A `class X(BaseTool): args_schema = ...` custom tool.
        if not any(isinstance(b, ast.Name) and b.id == "BaseTool" for b in cls.bases):
            return None
        has_schema = any(
            isinstance(s, ast.AnnAssign | ast.Assign) and "args_schema" in _assigned_names(s)
            for s in cls.body
        )
        return SemanticNode(
            SemanticTag.TOOL_DEF,
            cls,
            self.name,
            {"name": Known(cls.name), "has_schema": Known(has_schema)},
        )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _resolve_cap(ctx: SourceTree, scope: Scope, call: ast.Call) -> tuple[Resolved, str]:
    at_call = resolve_call_keyword(ctx, scope, call, "max_iter")
    if at_call is ABSENT:
        return Known(_MAX_ITER_DEFAULT), "framework_default"
    if at_call is UNKNOWN:
        return UNKNOWN, "unknown"
    return at_call, "explicit"


def _assigned_names(stmt: ast.stmt) -> set[str]:
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return {stmt.target.id}
    if isinstance(stmt, ast.Assign):
        return {t.id for t in stmt.targets if isinstance(t, ast.Name)}
    return set()


def _all_params_annotated(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    params = [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]
    real = [a for a in params if a.arg not in ("self", "cls")]
    return bool(real) and all(a.annotation is not None for a in real)
