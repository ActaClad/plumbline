"""Shared static value resolution (ADR-0004 D3).

One resolver, used by all adapters, decides whether a framework attribute
(timeout, temperature, tools, …) is statically Known(value), provably ABSENT,
or UNKNOWN. This logic is subtle — it decides, e.g., whether
`client = OpenAI(timeout=30)` silences PLB-RES-001 — so it lives in one place
and behaves identically across adapters.

The tri-state (ADR-0004 D2) is the precision mechanism: a High-confidence rule
fires only on ABSENT, never on UNKNOWN. So this module errs toward UNKNOWN
whenever a value cannot be pinned to a constant.
"""

from __future__ import annotations

import ast

from ..model import ABSENT, UNKNOWN, Known, Resolved
from .ast_layer import Scope, SourceTree

_MAX_DEPTH = 20  # cycle/blow-up guard for assignment chains


def resolve_value(st: SourceTree, scope: Scope, node: ast.expr) -> Resolved:
    """Resolve an expression to Known(constant) where statically determinable,
    else UNKNOWN. Walks single-assignment name bindings up the scope chain."""
    return _resolve(st, scope, node, frozenset())


def _resolve(st: SourceTree, scope: Scope, node: ast.expr, seen: frozenset[str]) -> Resolved:
    if isinstance(node, ast.Constant):
        return Known(node.value)

    # Negative/positive numeric literals: -1, +2.0
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
        inner = _resolve(st, scope, node.operand, seen)
        if isinstance(inner, Known) and isinstance(inner.value, int | float):
            return Known(-inner.value if isinstance(node.op, ast.USub) else +inner.value)
        return UNKNOWN

    if isinstance(node, ast.Name):
        return _resolve_name(st, scope, node.id, seen)

    return UNKNOWN


def _resolve_name(st: SourceTree, scope: Scope, name: str, seen: frozenset[str]) -> Resolved:
    if name in seen or len(seen) >= _MAX_DEPTH:
        return UNKNOWN  # cyclic or pathologically deep -> give up honestly
    s: Scope | None = scope
    while s is not None:
        if name in s.params:
            return UNKNOWN  # a parameter can be anything at call time
        rhss = s.assigns.get(name)
        if rhss is not None:
            if len(rhss) != 1:
                return UNKNOWN  # multiple assignments: can't pin the value
            return _resolve(st, s, rhss[0], seen | {name})
        s = s.parent
    return UNKNOWN  # imported, global from another module, or builtin


def resolve_call_keyword(st: SourceTree, scope: Scope, call: ast.Call, name: str) -> Resolved:
    """Resolve keyword argument `name` on a call.

    - present and pinnable      -> Known(value)
    - present but unresolvable  -> UNKNOWN
    - absent, no **kwargs spread -> ABSENT
    - absent but **kwargs present -> UNKNOWN (the dict may carry it)
    """
    has_kwargs_spread = False
    for kw in call.keywords:
        if kw.arg is None:
            has_kwargs_spread = True
        elif kw.arg == name:
            return resolve_value(st, scope, kw.value)
    return UNKNOWN if has_kwargs_spread else ABSENT


def root_name_of(node: ast.expr) -> str | None:
    """Leftmost Name in an attribute/call chain.

    `client.chat.completions.create` -> "client";  `foo()` -> "foo".
    """
    cur: ast.expr = node
    while True:
        if isinstance(cur, ast.Name):
            return cur.id
        if isinstance(cur, ast.Attribute):
            cur = cur.value
        elif isinstance(cur, ast.Call):
            cur = cur.func
        else:
            return None


def single_assignment(st: SourceTree, scope: Scope, name: str) -> ast.expr | None:
    """The sole RHS expression bound to `name` in the nearest enclosing scope,
    or None if the name is unbound, a parameter, or assigned more than once."""
    s: Scope | None = scope
    while s is not None:
        if name in s.params:
            return None
        rhss = s.assigns.get(name)
        if rhss is not None:
            return rhss[0] if len(rhss) == 1 else None
        s = s.parent
    return None
