"""Golden tests for the crewai adapter (adapter-contract.md §9, §6)."""

from __future__ import annotations

from plumbline.adapters import ADAPTERS
from plumbline.adapters.base import collect_semantics
from plumbline.adapters.crewai import CrewAIAdapter
from plumbline.core.ast_layer import parse
from plumbline.model import Known, Resolved, SemanticNode, SemanticTag


def _annotate(src: str) -> list[SemanticNode]:
    return list(CrewAIAdapter().annotate(parse("a.py", src)))


def _one(src: str, tag: SemanticTag) -> SemanticNode:
    nodes = [n for n in _annotate(src) if n.tag is tag]
    assert len(nodes) == 1, f"expected exactly one {tag}, got {len(nodes)}"
    return nodes[0]


def _attr(src: str, tag: SemanticTag, key: str) -> Resolved:
    return _one(src, tag).attrs[key]


# --- agent / crew construction + max_iter -> normalized max_iterations ---------


def test_agent_bare_is_framework_default_bounded() -> None:
    src = "from crewai import Agent\na = Agent(role='r', goal='g', backstory='b')\n"
    n = _one(src, SemanticTag.AGENT_CREATE)
    assert n.attrs["max_iterations"] == Known(25)
    assert n.attrs["max_iterations_source"] == Known("framework_default")
    assert n.attrs["framework"] == Known("crewai")


def test_agent_explicit_max_iter_none_is_uncapped() -> None:
    src = "from crewai import Agent\na = Agent(role='r', goal='g', max_iter=None)\n"
    n = _one(src, SemanticTag.AGENT_CREATE)
    assert n.attrs["max_iterations"] == Known(None)
    assert n.attrs["max_iterations_source"] == Known("explicit")


def test_agent_explicit_max_iter_value() -> None:
    src = "from crewai import Agent\na = Agent(role='r', goal='g', max_iter=5)\n"
    assert _attr(src, SemanticTag.AGENT_CREATE, "max_iterations") == Known(5)


def test_crew_is_agent_create() -> None:
    src = "from crewai import Crew\nc = Crew(agents=a, tasks=t)\n"
    assert _attr(src, SemanticTag.AGENT_CREATE, "max_iterations") == Known(25)


def test_kickoff_is_agent_invoke() -> None:
    src = "from crewai import Crew\nc = Crew(agents=a, tasks=t)\nc.kickoff()\n"
    assert any(n.tag is SemanticTag.AGENT_INVOKE for n in _annotate(src))


# --- tools --------------------------------------------------------------------


def test_tool_decorator_typed_has_schema() -> None:
    src = (
        "from crewai.tools import tool\n@tool('search')\ndef search(q: str) -> str:\n    return q\n"
    )
    n = _one(src, SemanticTag.TOOL_DEF)
    assert n.attrs["has_schema"] == Known(True)
    assert n.attrs["name"] == Known("search")


def test_tool_decorator_untyped_no_schema() -> None:
    src = "from crewai.tools import tool\n@tool('search')\ndef search(q):\n    return q\n"
    assert _attr(src, SemanticTag.TOOL_DEF, "has_schema") == Known(False)


def test_basetool_subclass_with_args_schema_has_schema() -> None:
    src = (
        "from crewai.tools import BaseTool\n"
        "class MyTool(BaseTool):\n"
        "    args_schema = MySchema\n"
        "    def _run(self, q):\n        return q\n"
    )
    n = _one(src, SemanticTag.TOOL_DEF)
    assert n.attrs["has_schema"] == Known(True)
    assert n.attrs["name"] == Known("MyTool")


def test_basetool_subclass_without_args_schema_no_schema() -> None:
    src = (
        "from crewai.tools import BaseTool\n"
        "class MyTool(BaseTool):\n"
        "    def _run(self, q):\n        return q\n"
    )
    assert _attr(src, SemanticTag.TOOL_DEF, "has_schema") == Known(False)


# --- gating + negative --------------------------------------------------------


def test_adapter_gated_off_without_trigger_import() -> None:
    st = parse("a.py", "x = 1\n")
    assert collect_semantics(st, ADAPTERS) == []


def test_plain_python_yields_no_annotations() -> None:
    assert _annotate("def f(x):\n    return x + 1\n") == []


def test_registered_in_adapters_with_priority_20() -> None:
    ca = [a for a in ADAPTERS if isinstance(a, CrewAIAdapter)]
    assert ca and ca[0].priority == 20
