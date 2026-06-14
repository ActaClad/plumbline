"""Tests for the AST layer (ADR-0009)."""

from __future__ import annotations

import ast

import pytest

from plumbline.core.ast_layer import ParseError, ScopeKind, parse, scan_suppressions


def test_syntax_error_raises_parse_error() -> None:
    with pytest.raises(ParseError, match="bad.py"):
        parse("bad.py", "def f(:\n")


def test_parent_map_links_child_to_parent() -> None:
    st = parse("a.py", "x = 1\n")
    assign = st.tree.body[0]
    assert isinstance(assign, ast.Assign)
    name = assign.targets[0]
    assert st.parent(name) is assign


def test_enclosing_statement_and_anchor() -> None:
    st = parse("a.py", "def f():\n    y = client.create(model='m')\n")
    call = next(n for n in ast.walk(st.tree) if isinstance(n, ast.Call))
    stmt = st.enclosing_statement(call)
    assert isinstance(stmt, ast.Assign)
    assert st.anchor_text(call) == "y = client.create(model='m')"


def test_segment_returns_exact_source() -> None:
    st = parse("a.py", "z = foo(1, 2)\n")
    call = next(n for n in ast.walk(st.tree) if isinstance(n, ast.Call))
    assert st.segment(call) == "foo(1, 2)"


def test_module_scope_records_assignments() -> None:
    st = parse("a.py", "TIMEOUT = 30\n")
    assert "TIMEOUT" in st.module_scope.assigns
    value = st.module_scope.assigns["TIMEOUT"][0]
    assert isinstance(value, ast.Constant) and value.value == 30


def test_function_scope_created_with_params() -> None:
    st = parse("a.py", "def f(a, b):\n    c = a\n")
    fn = st.tree.body[0]
    assert isinstance(fn, ast.FunctionDef)
    body_stmt = fn.body[0]
    scope = st.scope_of(body_stmt)
    assert scope.kind is ScopeKind.FUNCTION
    assert scope.params == {"a", "b"}
    assert "c" in scope.assigns


def test_nested_function_scope_parent_chain() -> None:
    src = "def outer():\n    def inner():\n        x = 1\n"
    st = parse("a.py", src)
    inner_assign = next(n for n in ast.walk(st.tree) if isinstance(n, ast.Assign))
    scope = st.scope_of(inner_assign)
    assert scope.kind is ScopeKind.FUNCTION
    assert scope.parent is not None and scope.parent.kind is ScopeKind.FUNCTION
    assert scope.parent.parent is not None and scope.parent.parent.kind is ScopeKind.MODULE


# --- imports ------------------------------------------------------------------


def test_import_plain() -> None:
    st = parse("a.py", "import openai\n")
    assert "openai" in st.imported_roots
    assert st.imports["openai"].module == "openai"
    assert st.imports["openai"].qualname == ""


def test_import_aliased() -> None:
    st = parse("a.py", "import openai as oa\n")
    assert st.imports["oa"].module == "openai"
    assert "openai" in st.imported_roots


def test_from_import_with_alias() -> None:
    st = parse("a.py", "from openai import OpenAI as Client\n")
    info = st.imports["Client"]
    assert info.module == "openai" and info.qualname == "OpenAI"
    assert "openai" in st.imported_roots


def test_dotted_import_root_recorded() -> None:
    st = parse("a.py", "from langchain.chat_models import ChatOpenAI\n")
    assert "langchain" in st.imported_roots
    assert st.imports["ChatOpenAI"].module == "langchain.chat_models"


# --- suppressions (ADR-0006 D6) ----------------------------------------------


def test_suppression_single_rule() -> None:
    s = scan_suppressions("x = f()  # plumb: ignore[PLB-RES-001]\n")
    assert s.by_line[1] == frozenset({"PLB-RES-001"})
    assert s.invalid_lines == ()


def test_suppression_multiple_rules_with_reason() -> None:
    s = scan_suppressions("x = f()  # plumb: ignore[PLB-RES-001, PLB-SEC-002] -- known safe\n")
    assert s.by_line[1] == frozenset({"PLB-RES-001", "PLB-SEC-002"})


def test_bare_ignore_is_invalid() -> None:
    s = scan_suppressions("x = f()  # plumb: ignore\n")
    assert s.invalid_lines == (1,)
    assert s.by_line == {}


def test_non_suppression_comment_ignored() -> None:
    s = scan_suppressions("x = f()  # just a normal comment\n")
    assert s.by_line == {} and s.invalid_lines == ()


def test_prose_comment_mentioning_directive_is_not_a_suppression() -> None:
    # A comment that DOCUMENTS the syntax must not be parsed as a directive
    # (the directive must start the comment, matched with .match). Plumbline's own
    # source has such comments — found by dogfooding `plumb scan src`.
    s = scan_suppressions("invalid: tuple  # bare `# plumb: ignore` with no rule id\n")
    assert s.invalid_lines == ()
    assert s.by_line == {}
    # but a real trailing directive still works
    s2 = scan_suppressions("x = f()  # plumb: ignore[PLB-RES-001]\n")
    assert s2.by_line == {1: frozenset({"PLB-RES-001"})}


def test_tokenizer_error_is_swallowed() -> None:
    # Unterminated string would raise TokenError; scan must degrade, not crash.
    s = scan_suppressions('x = "unterminated\n')
    assert s.by_line == {} and s.invalid_lines == ()
