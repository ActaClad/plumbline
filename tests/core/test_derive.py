"""Derived-semantics tests — AGENT_LOOP detection + loop properties (ADR-0012)."""

from __future__ import annotations

from plumbline.adapters import ADAPTERS
from plumbline.adapters.base import collect_semantics
from plumbline.core.ast_layer import parse
from plumbline.core.derive import derive_semantics
from plumbline.model import Known, Resolved, SemanticNode, SemanticTag

_PRELUDE = "from openai import OpenAI\nc = OpenAI()\n"


def _loops(src: str) -> list[SemanticNode]:
    st = parse("a.py", _PRELUDE + src)
    collected = collect_semantics(st, ADAPTERS)
    return [n for n in derive_semantics(st, collected) if n.tag is SemanticTag.AGENT_LOOP]


def _one(src: str) -> SemanticNode:
    loops = _loops(src)
    assert len(loops) == 1, f"expected exactly one AGENT_LOOP, got {len(loops)}"
    return loops[0]


def _props(src: str) -> tuple[Resolved, Resolved]:
    n = _one(src)
    return n.attrs["has_iteration_cap"], n.attrs["has_goal_exit"]


_CALL = "    c.chat.completions.create(model='m')\n"


# --- population: only loops that contain a model call are tagged ---------------


def test_loop_with_llm_call_is_tagged() -> None:
    assert len(_loops("while True:\n" + _CALL)) == 1


def test_loop_without_llm_call_is_not_tagged() -> None:
    assert _loops("while True:\n    x = 1\n") == []


def test_llm_call_in_nested_def_does_not_tag_the_loop() -> None:
    # The call belongs to the nested function's scope, not the loop (ADR-0012 D2).
    src = (
        "while True:\n    def helper():\n        c.chat.completions.create(model='m')\n    x = 1\n"
    )
    assert _loops(src) == []


# --- the four worked cases from ADR-0012 D3 -----------------------------------


def test_while_true_no_break_is_uncapped_and_no_goal_exit() -> None:
    cap, goal = _props("while True:\n" + _CALL)
    assert cap == Known(False)
    assert goal == Known(False)


def test_while_true_with_goal_break_is_uncapped_but_has_goal_exit() -> None:
    cap, goal = _props("while True:\n" + _CALL + "    if done():\n        break\n")
    assert cap == Known(False)  # no hard cap -> AGT-001 still fires
    assert goal == Known(True)  # terminates on goal -> AGT-002 silent


def test_for_range_is_capped() -> None:
    cap, goal = _props("for _ in range(10):\n" + _CALL)
    assert cap == Known(True)
    assert goal == Known(True)


def test_while_counter_bound_is_capped() -> None:
    src = "n = 0\nwhile True:\n" + _CALL + "    n += 1\n    if n > 8:\n        break\n"
    cap, goal = _props(src)
    assert cap == Known(True)
    assert goal == Known(True)


# --- additional precision cases -----------------------------------------------


def test_for_over_literal_list_is_capped() -> None:
    cap, _ = _props("for q in ['a', 'b']:\n" + _CALL)
    assert cap == Known(True)


def test_for_over_name_is_unknown_cap() -> None:
    # An arbitrary iterable could be an infinite generator -> do not claim a cap.
    cap, _ = _props(
        "def run(items):\n  for q in items:\n    c.chat.completions.create(model='m')\n"
    )
    assert cap is not Known(True)
    assert cap is not Known(False)


def test_while_condition_has_goal_exit() -> None:
    src = "def run(done):\n  while not done:\n    c.chat.completions.create(model='m')\n"
    n = [x for x in _loops_from_full(src) if x.tag is SemanticTag.AGENT_LOOP]
    assert n[0].attrs["has_goal_exit"] == Known(True)
    # a real condition -> we can't claim a hard cap either way
    assert n[0].attrs["has_iteration_cap"] not in (Known(True), Known(False))


def test_return_counts_as_goal_exit() -> None:
    cap, goal = _props("while True:\n" + _CALL + "    if done():\n        return\n")
    assert goal == Known(True)


def test_break_in_nested_loop_does_not_count_as_outer_goal_exit() -> None:
    src = "while True:\n" + _CALL + "    for j in range(3):\n        break\n"
    _, goal = _props(src)
    assert goal == Known(False)  # the break binds to the inner for, not the outer while


# helper for sources that define their own prelude-free function bodies
def _loops_from_full(src: str) -> list[SemanticNode]:
    st = parse("a.py", _PRELUDE + src)
    collected = collect_semantics(st, ADAPTERS)
    return derive_semantics(st, collected)


def test_determinism_double_run() -> None:
    src = "while True:\n" + _CALL
    st = parse("a.py", _PRELUDE + src)
    collected = collect_semantics(st, ADAPTERS)
    a = derive_semantics(st, collected)
    b = derive_semantics(st, collected)
    key = [(n.tag, getattr(n.node, "lineno", 0)) for n in a]
    assert key == [(n.tag, getattr(n.node, "lineno", 0)) for n in b]
