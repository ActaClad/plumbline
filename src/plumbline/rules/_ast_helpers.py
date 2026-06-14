"""Shared AST helpers for detectors. No `RULE` attribute -> skipped by discovery
(ADR-0005). Keep these small and dependency-free so rules stay self-contained.
"""

from __future__ import annotations

import ast

from ..core.ast_layer import SourceTree


def enclosing_try_body(tree: SourceTree, node: ast.AST) -> ast.Try | None:
    """The nearest Try whose *try body* (not a handler/else/finally) contains node."""
    child: ast.AST = node
    parent = tree.parent(child)
    while parent is not None:
        if isinstance(parent, ast.Try) and _contains(parent.body, child):
            return parent
        child = parent
        parent = tree.parent(child)
    return None


def _contains(body: list[ast.stmt], target: ast.AST) -> bool:
    return any(target is stmt or target in ast.walk(stmt) for stmt in body)


def try_catches(try_node: ast.Try, names: frozenset[str]) -> bool:
    """True if any handler is bare (`except:`) or catches an exception whose simple
    name (or attribute tail, e.g. `json.JSONDecodeError`) is in `names`."""
    for handler in try_node.handlers:
        if handler.type is None:
            return True
        for exc in _handler_types(handler.type):
            if exc in names:
                return True
    return False


def _handler_types(node: ast.expr) -> list[str]:
    # `except E`, `except (A, B)`, `except mod.E`
    targets = node.elts if isinstance(node, ast.Tuple) else [node]
    out: list[str] = []
    for t in targets:
        if isinstance(t, ast.Name):
            out.append(t.id)
        elif isinstance(t, ast.Attribute):
            out.append(t.attr)
    return out
