"""Tests for the shared value resolver (ADR-0004 D3)."""

from __future__ import annotations

import ast

from plumbline.core.ast_layer import parse
from plumbline.core.values import (
    resolve_call_keyword,
    resolve_value,
    root_name_of,
    single_assignment,
)
from plumbline.model import ABSENT, UNKNOWN, Known


def _only_call(src: str) -> tuple[ast.Call, object]:
    st = parse("a.py", src)
    call = next(n for n in ast.walk(st.tree) if isinstance(n, ast.Call))
    return call, st


def _resolve_kw(src: str, name: str) -> object:
    st = parse("a.py", src)
    call = next(n for n in ast.walk(st.tree) if isinstance(n, ast.Call))
    return resolve_call_keyword(st, st.scope_of(call), call, name)


# --- resolve_value ------------------------------------------------------------


def test_constant_resolves_to_known() -> None:
    st = parse("a.py", "x = 30\n")
    assign = st.tree.body[0]
    assert isinstance(assign, ast.Assign)
    r = resolve_value(st, st.module_scope, assign.value)
    assert r == Known(30)


def test_negative_numeric_literal() -> None:
    st = parse("a.py", "x = -1\n")
    assign = st.tree.body[0]
    assert isinstance(assign, ast.Assign)
    assert resolve_value(st, st.module_scope, assign.value) == Known(-1)


def test_name_with_single_constant_assignment() -> None:
    st = parse("a.py", "T = 30\ny = T\n")
    y = st.tree.body[1]
    assert isinstance(y, ast.Assign)
    assert resolve_value(st, st.module_scope, y.value) == Known(30)


def test_name_with_multiple_assignments_is_unknown() -> None:
    st = parse("a.py", "T = 30\nT = 60\ny = T\n")
    y = st.tree.body[2]
    assert isinstance(y, ast.Assign)
    assert resolve_value(st, st.module_scope, y.value) is UNKNOWN


def test_unbound_name_is_unknown() -> None:
    st = parse("a.py", "y = SOMETHING\n")
    y = st.tree.body[0]
    assert isinstance(y, ast.Assign)
    assert resolve_value(st, st.module_scope, y.value) is UNKNOWN


def test_cyclic_assignment_is_unknown_not_infinite() -> None:
    st = parse("a.py", "x = x\ny = x\n")
    y = st.tree.body[1]
    assert isinstance(y, ast.Assign)
    assert resolve_value(st, st.module_scope, y.value) is UNKNOWN


def test_parameter_is_unknown() -> None:
    st = parse("a.py", "def f(t):\n    y = t\n")
    fn = st.tree.body[0]
    assert isinstance(fn, ast.FunctionDef)
    y = fn.body[0]
    assert isinstance(y, ast.Assign)
    assert resolve_value(st, st.scope_of(y), y.value) is UNKNOWN


def test_resolves_module_constant_from_within_function() -> None:
    st = parse("a.py", "T = 30\ndef f():\n    y = T\n")
    fn = st.tree.body[1]
    assert isinstance(fn, ast.FunctionDef)
    y = fn.body[0]
    assert isinstance(y, ast.Assign)
    assert resolve_value(st, st.scope_of(y), y.value) == Known(30)


# --- resolve_call_keyword -----------------------------------------------------


def test_keyword_present_constant() -> None:
    assert _resolve_kw("client.create(timeout=30)\n", "timeout") == Known(30)


def test_keyword_absent_is_absent() -> None:
    assert _resolve_kw("client.create(model='m')\n", "timeout") is ABSENT


def test_keyword_present_unresolvable_is_unknown() -> None:
    assert _resolve_kw("client.create(timeout=cfg.T)\n", "timeout") is UNKNOWN


def test_keyword_absent_with_kwargs_spread_is_unknown() -> None:
    # **opts could carry timeout -> honest UNKNOWN, not ABSENT.
    assert _resolve_kw("client.create(model='m', **opts)\n", "timeout") is UNKNOWN


def test_keyword_resolved_through_variable() -> None:
    st = parse("a.py", "T = 30\nclient.create(timeout=T)\n")
    call = next(n for n in ast.walk(st.tree) if isinstance(n, ast.Call))
    assert resolve_call_keyword(st, st.scope_of(call), call, "timeout") == Known(30)


# --- root_name_of / single_assignment -----------------------------------------


def test_root_name_of_attribute_chain() -> None:
    call, _ = _only_call("client.chat.completions.create()\n")
    assert root_name_of(call.func) == "client"


def test_root_name_of_plain_call() -> None:
    call, _ = _only_call("foo()\n")
    assert root_name_of(call.func) == "foo"


def test_single_assignment_returns_rhs() -> None:
    st = parse("a.py", "client = OpenAI()\nclient.create()\n")
    rhs = single_assignment(st, st.module_scope, "client")
    assert isinstance(rhs, ast.Call)


def test_single_assignment_none_when_reassigned() -> None:
    st = parse("a.py", "client = OpenAI()\nclient = OpenAI()\n")
    assert single_assignment(st, st.module_scope, "client") is None
