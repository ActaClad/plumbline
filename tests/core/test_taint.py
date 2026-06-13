"""Taint engine — executable spec (taint-engine.md §8, ADR-0003)."""

from __future__ import annotations

import ast

from plumbline.adapters import ADAPTERS
from plumbline.adapters.base import SemanticIndex, collect_semantics
from plumbline.core.ast_layer import parse
from plumbline.core.taint import TaintLabel, analyze_taint

U = TaintLabel.USER_INPUT
LLM = TaintLabel.LLM_OUTPUT
HTTP = TaintLabel.EXTERNAL_HTTP
PII = TaintLabel.PII

_OPENAI = "from openai import OpenAI\nc = OpenAI()\n"


def _sink_arg(src: str, sink: str = "sink") -> frozenset[TaintLabel]:
    st = parse("a.py", src)
    view = analyze_taint(st, SemanticIndex(collect_semantics(st, ADAPTERS)))
    for n in ast.walk(st.tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == sink:
            return view.labels(n.args[0])
    raise AssertionError(f"no {sink}() call found")


# --- sources ------------------------------------------------------------------


def test_input_is_user_input() -> None:
    assert _sink_arg("u = input()\nsink(u)\n") == frozenset({U})


def test_llm_call_result_is_llm_output() -> None:
    src = _OPENAI + "r = c.chat.completions.create(model='m')\nsink(r)\n"
    assert _sink_arg(src) == frozenset({LLM})


def test_requests_get_is_external_http() -> None:
    assert _sink_arg("import requests\nr = requests.get(url)\nsink(r)\n") == frozenset({HTTP})


def test_constant_is_untainted() -> None:
    assert _sink_arg("sink('literal')\n") == frozenset()


# --- propagation rows (taint-engine §3) ---------------------------------------


def test_fstring_propagates() -> None:
    assert _sink_arg("u = input()\np = f'hello {u}'\nsink(p)\n") == frozenset({U})


def test_concatenation_propagates() -> None:
    assert _sink_arg("u = input()\np = 'x: ' + u\nsink(p)\n") == frozenset({U})


def test_str_method_propagates_from_receiver() -> None:
    assert _sink_arg("u = input()\nsink(u.strip().lower())\n") == frozenset({U})


def test_join_propagates() -> None:
    assert _sink_arg("u = input()\nsink(', '.join([u, 'x']))\n") == frozenset({U})


def test_attribute_access_propagates() -> None:
    src = "import requests\nr = requests.get(x)\nsink(r.text)\n"
    assert _sink_arg(src) == frozenset({HTTP})


def test_subscript_propagates() -> None:
    assert _sink_arg("u = input()\nd = {'k': u}\nsink(d['k'])\n") == frozenset({U})


def test_conditional_expr_unions() -> None:
    assert _sink_arg("u = input()\nsink(u if flag else 'safe')\n") == frozenset({U})


def test_json_loads_propagates() -> None:
    src = _OPENAI + "import json\nr = c.chat.completions.create(model='m')\nsink(json.loads(r))\n"
    assert _sink_arg(src) == frozenset({LLM})


def test_assignment_chain() -> None:
    assert _sink_arg("u = input()\na = u\nb = a\nsink(b)\n") == frozenset({U})


def test_tuple_unpacking_propagates() -> None:
    assert _sink_arg("u = input()\nx, y = u, u\nsink(x)\n") == frozenset({U})


# --- sanitizers ---------------------------------------------------------------


def test_int_sanitizes() -> None:
    assert _sink_arg("u = input()\nsink(int(u))\n") == frozenset()


def test_len_sanitizes() -> None:
    assert _sink_arg("u = input()\nsink(len(u))\n") == frozenset()


def test_comparison_is_clean() -> None:
    assert _sink_arg("u = input()\nsink(u == 'yes')\n") == frozenset()


# --- control flow -------------------------------------------------------------


def test_branch_union_taints_after_if() -> None:
    src = "p = 'safe'\nif flag:\n    p = input()\nsink(p)\n"
    assert _sink_arg(src) == frozenset({U})


def test_loop_carried_flow() -> None:
    # y reads x before x is tainted on the first pass; the fixpoint must catch
    # that a later iteration taints x, so y is USER_INPUT after the loop.
    src = "x = ''\nfor i in r:\n    y = x\n    x = input()\nsink(y)\n"
    assert _sink_arg(src) == frozenset({U})


# --- function summaries (taint-engine §4) -------------------------------------


def test_summary_propagates_flagged_param() -> None:
    src = "def wrap(a, b):\n    return a\nu = input()\nsink(wrap(u, 'safe'))\n"
    assert _sink_arg(src) == frozenset({U})


def test_summary_does_not_propagate_unflagged_param() -> None:
    src = "def wrap(a, b):\n    return a\nu = input()\nsink(wrap('safe', u))\n"
    assert _sink_arg(src) == frozenset()


def test_recursive_summary_converges() -> None:
    src = (
        "def rec(a, n):\n"
        "    if n == 0:\n"
        "        return a\n"
        "    return rec(a, n - 1)\n"
        "u = input()\n"
        "sink(rec(u, 3))\n"
    )
    assert _sink_arg(src) == frozenset({U})


def test_summary_through_concat_in_body() -> None:
    src = "def deco(a):\n    return '<' + a + '>'\nu = input()\nsink(deco(u))\n"
    assert _sink_arg(src) == frozenset({U})


# --- v1 boundary negatives (taint-engine §3 / ADR-0003 D6) --------------------


def test_unknown_call_returns_untainted() -> None:
    assert _sink_arg("u = input()\nsink(mystery(u))\n") == frozenset()


def test_instance_attribute_not_tracked() -> None:
    # self.x assignment is a v1 boundary non-goal -> no taint through it.
    src = "u = input()\nclass C:\n    def m(self):\n        self.x = u\n        sink(self.x)\n"
    assert _sink_arg(src) == frozenset()


# --- parameter sources --------------------------------------------------------


def test_web_handler_param_is_user_input() -> None:
    src = "@app.post('/x')\ndef handler(body):\n    sink(body)\n"
    assert _sink_arg(src) == frozenset({U})


def test_pii_named_param_is_pii() -> None:
    src = "def send(user_email):\n    sink(user_email)\n"
    assert _sink_arg(src) == frozenset({PII})


def test_plain_param_is_untainted() -> None:
    src = "def f(x):\n    sink(x)\n"
    assert _sink_arg(src) == frozenset()


# --- witness + determinism ----------------------------------------------------


def test_witness_path_present_for_tainted_node() -> None:
    st = parse("a.py", "u = input()\np = f'{u}'\nsink(p)\n")
    view = analyze_taint(st, SemanticIndex(collect_semantics(st, ADAPTERS)))
    call = next(
        n
        for n in ast.walk(st.tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sink"
    )
    hops = view.witness(call.args[0], U)
    assert hops and "input()" in hops[0].description


def test_analysis_is_deterministic() -> None:
    src = _OPENAI + "r = c.chat.completions.create(model='m')\np = f'{r}'\nsink(p)\n"
    a = _sink_arg(src)
    b = _sink_arg(src)
    assert a == b == frozenset({LLM})
