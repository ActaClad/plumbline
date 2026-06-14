"""Derived semantics — cross-cutting tags no single adapter can see (ADR-0012).

Runs after every adapter (`collect_semantics`) and before the `SemanticIndex` /
taint are built. Pure and deterministic: a function of the AST plus the already
collected semantic nodes, with no I/O and no adapter calls.

v1 derives exactly one tag, `AGENT_LOOP`: a `while`/`for` whose body contains a
model call regardless of which adapter tagged it. That framework-independence is
what lets one AGT rule cover LangChain, CrewAI, and hand-rolled loops alike.
See `adapter-contract.md` §10.
"""

from __future__ import annotations

import ast
from collections.abc import Sequence

from ..model import UNKNOWN, Known, Resolved, SemanticNode, SemanticTag
from .ast_layer import SourceTree

ADAPTER_NAME = "core:derive"


def derive_semantics(tree: SourceTree, collected: Sequence[SemanticNode]) -> list[SemanticNode]:
    """Compute cross-cutting semantic nodes (ADR-0012 D1). Deterministic."""
    llm_call_ids = {id(sn.node) for sn in collected if sn.tag is SemanticTag.LLM_CALL}
    out: list[SemanticNode] = []
    for node in ast.walk(tree.tree):
        if isinstance(node, ast.While | ast.For) and _body_has_llm_call(node, llm_call_ids):
            out.append(
                SemanticNode(
                    SemanticTag.AGENT_LOOP,
                    node,
                    ADAPTER_NAME,
                    {
                        "has_iteration_cap": _has_iteration_cap(node),
                        "has_goal_exit": _has_goal_exit(node),
                    },
                )
            )
    # Sorted output for a stable function contract (the index re-sorts anyway).
    out.sort(key=lambda sn: (getattr(sn.node, "lineno", 0), getattr(sn.node, "col_offset", 0)))
    return out


# --------------------------------------------------------------------------- #
# AGENT_LOOP population (ADR-0012 D2): a loop body containing a model call.
# --------------------------------------------------------------------------- #


def _loop_body(node: ast.While | ast.For) -> list[ast.stmt]:
    return [*node.body, *node.orelse]


def _walk_within_loop(stmts: Sequence[ast.stmt]) -> list[ast.AST]:
    """All descendant nodes of `stmts`, NOT descending into nested function or
    class definitions (their calls belong to a different scope, ADR-0012 D2)."""
    out: list[ast.AST] = []
    stack: list[ast.AST] = list(stmts)
    while stack:
        cur = stack.pop()
        out.append(cur)
        if isinstance(cur, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        stack.extend(ast.iter_child_nodes(cur))
    return out


def _body_has_llm_call(node: ast.While | ast.For, llm_call_ids: set[int]) -> bool:
    return any(id(n) in llm_call_ids for n in _walk_within_loop(_loop_body(node)))


# --------------------------------------------------------------------------- #
# Loop property 1: has_iteration_cap (ADR-0012 D3).
# --------------------------------------------------------------------------- #


def _has_iteration_cap(node: ast.While | ast.For) -> Resolved:
    if isinstance(node, ast.For):
        if _is_finite_iterable(node.iter):
            return Known(True)
        return UNKNOWN
    # while:
    if not _is_truthy_const(node.test):
        return UNKNOWN  # a real condition may or may not bound it — don't claim.
    return Known(_has_counter_bound(node))


def _is_finite_iterable(node: ast.expr) -> bool:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
        return True
    return isinstance(node, ast.List | ast.Tuple | ast.Set)


def _has_counter_bound(loop: ast.While) -> bool:
    """A `while True` is capped when some integer name is `+=`-incremented in the
    body and that same name is compared somewhere in the body (the bound check)."""
    incremented = {
        _name(stmt.target)
        for stmt in _walk_within_loop(loop.body)
        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add)
    }
    incremented.discard("")
    if not incremented:
        return False
    for n in _walk_within_loop(loop.body):
        if isinstance(n, ast.Compare):
            names = {x.id for x in ast.walk(n) if isinstance(x, ast.Name)}
            if names & incremented:
                return True
    return False


# --------------------------------------------------------------------------- #
# Loop property 2: has_goal_exit (ADR-0012 D3).
# --------------------------------------------------------------------------- #


def _has_goal_exit(node: ast.While | ast.For) -> Resolved:
    if isinstance(node, ast.For):
        return Known(True)  # the iterator exhausts.
    if not _is_truthy_const(node.test):
        return Known(True)  # the test can go false.
    return Known(_reachable_break_or_return(node.body))


def _reachable_break_or_return(stmts: Sequence[ast.stmt]) -> bool:
    """A `break` (belonging to THIS loop, not a nested one) or any `return`
    reachable in the body, not descending into nested defs."""
    stack: list[ast.AST] = list(stmts)
    while stack:
        cur = stack.pop()
        if isinstance(cur, ast.Return | ast.Break):
            return True
        if isinstance(cur, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if isinstance(cur, ast.For | ast.AsyncFor | ast.While):
            # A `break` inside a nested loop binds to it, so we do not treat the
            # nested loop's breaks as ours — but a `return` anywhere still exits
            # ours. Recurse only for returns (not descending into nested defs).
            if _reachable_return(cur.body) or _reachable_return(getattr(cur, "orelse", [])):
                return True
            continue
        stack.extend(ast.iter_child_nodes(cur))
    return False


def _reachable_return(stmts: Sequence[ast.stmt]) -> bool:
    """Any `return` reachable in `stmts`, not descending into nested defs."""
    stack: list[ast.AST] = list(stmts)
    while stack:
        cur = stack.pop()
        if isinstance(cur, ast.Return):
            return True
        if isinstance(cur, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        stack.extend(ast.iter_child_nodes(cur))
    return False


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _is_truthy_const(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and bool(node.value)


def _name(node: ast.expr) -> str:
    return node.id if isinstance(node, ast.Name) else ""
