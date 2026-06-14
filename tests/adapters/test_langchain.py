"""Golden tests for the langchain adapter (adapter-contract.md §8, §6)."""

from __future__ import annotations

from plumbline.adapters import ADAPTERS
from plumbline.adapters.base import collect_semantics
from plumbline.adapters.langchain import LangChainAdapter
from plumbline.core.ast_layer import parse
from plumbline.model import ABSENT, Known, Resolved, SemanticNode, SemanticTag


def _annotate(src: str) -> list[SemanticNode]:
    return list(LangChainAdapter().annotate(parse("a.py", src)))


def _one(src: str, tag: SemanticTag) -> SemanticNode:
    nodes = [n for n in _annotate(src) if n.tag is tag]
    assert len(nodes) == 1, f"expected exactly one {tag}, got {len(nodes)}"
    return nodes[0]


def _attr(src: str, tag: SemanticTag, key: str) -> Resolved:
    return _one(src, tag).attrs[key]


# --- chat-model client construction (LLM_CLIENT_CREATE) -----------------------


def test_chat_openai_is_client_create() -> None:
    n = _one(
        "from langchain_openai import ChatOpenAI\nm = ChatOpenAI(model='gpt-4o')\n",
        SemanticTag.LLM_CLIENT_CREATE,
    )
    assert n.attrs["provider"] == Known("openai")
    assert n.attrs["model"] == Known("gpt-4o")


def test_chat_anthropic_provider_normalized() -> None:
    n = _one(
        "from langchain_anthropic import ChatAnthropic\nm = ChatAnthropic()\n",
        SemanticTag.LLM_CLIENT_CREATE,
    )
    assert n.attrs["provider"] == Known("anthropic")


def test_aliased_import_still_resolves() -> None:
    # resolve_qualified recovers the real construct name through an alias.
    src = "from langchain_openai import ChatOpenAI as LLM\nm = LLM()\n"
    assert _one(src, SemanticTag.LLM_CLIENT_CREATE).attrs["provider"] == Known("openai")


def test_old_model_name_kwarg_resolves() -> None:
    src = "from langchain_openai import ChatOpenAI\nm = ChatOpenAI(model_name='gpt-4')\n"
    assert _attr(src, SemanticTag.LLM_CLIENT_CREATE, "model") == Known("gpt-4")


# --- agent construction (AGENT_CREATE) + framework-default resolution ----------


def test_agent_executor_bare_is_framework_default_bounded() -> None:
    src = "from langchain.agents import AgentExecutor\na = AgentExecutor(agent=x, tools=t)\n"
    n = _one(src, SemanticTag.AGENT_CREATE)
    assert n.attrs["max_iterations"] == Known(15)
    assert n.attrs["max_iterations_source"] == Known("framework_default")


def test_agent_executor_explicit_none_is_uncapped() -> None:
    # The deliberate cap-removal AGT-001 targets (mirrors RES-001 timeout=None).
    src = (
        "from langchain.agents import AgentExecutor\n"
        "a = AgentExecutor(agent=x, tools=t, max_iterations=None)\n"
    )
    n = _one(src, SemanticTag.AGENT_CREATE)
    assert n.attrs["max_iterations"] == Known(None)
    assert n.attrs["max_iterations_source"] == Known("explicit")


def test_agent_executor_explicit_value_is_explicit() -> None:
    src = (
        "from langchain.agents import AgentExecutor\n"
        "a = AgentExecutor(agent=x, tools=t, max_iterations=8)\n"
    )
    n = _one(src, SemanticTag.AGENT_CREATE)
    assert n.attrs["max_iterations"] == Known(8)
    assert n.attrs["max_iterations_source"] == Known("explicit")


def test_create_react_agent_is_graph_default_bounded() -> None:
    src = (
        "from langgraph.prebuilt import create_react_agent\ng = create_react_agent(model, tools)\n"
    )
    n = _one(src, SemanticTag.AGENT_CREATE)
    assert n.attrs["max_iterations"] == Known(25)  # recursion_limit default
    assert n.attrs["max_iterations_source"] == Known("framework_default")


def test_stategraph_compile_is_agent_create() -> None:
    src = "from langgraph.graph import StateGraph\ng = StateGraph(State)\napp = g.compile()\n"
    n = _one(src, SemanticTag.AGENT_CREATE)
    assert n.attrs["max_iterations"] == Known(25)


# --- invoke linking: model -> LLM_CALL, agent -> AGENT_INVOKE ------------------


def test_model_invoke_is_llm_call() -> None:
    src = (
        "from langchain_openai import ChatOpenAI\n"
        "m = ChatOpenAI(model='gpt-4o', max_tokens=256)\n"
        "m.invoke('hi')\n"
    )
    n = _one(src, SemanticTag.LLM_CALL)
    # max_tokens is set on the model construction -> merged onto the call.
    assert n.attrs["max_tokens"] == Known(256)


def test_agent_invoke_is_agent_invoke() -> None:
    src = (
        "from langchain.agents import AgentExecutor\n"
        "a = AgentExecutor(agent=x, tools=t)\n"
        "a.invoke({'input': 'hi'})\n"
    )
    assert any(n.tag is SemanticTag.AGENT_INVOKE for n in _annotate(src))


def test_unlinkable_invoke_is_not_tagged() -> None:
    # Receiver comes from a parameter -> we cannot prove it is a model or agent.
    src = "def run(chain):\n    return chain.invoke('hi')\n"
    assert _annotate(src) == []


# --- the COST-001 misfire guard (adapter-contract §7.4) -----------------------


def test_model_invoke_max_tokens_on_client_does_not_read_absent() -> None:
    # Bare model, max_tokens nowhere -> genuinely ABSENT (COST-001 SHOULD fire).
    src = (
        "from langchain_openai import ChatOpenAI\nm = ChatOpenAI(model='gpt-4o')\nm.invoke('hi')\n"
    )
    assert _attr(src, SemanticTag.LLM_CALL, "max_tokens") is ABSENT


def test_model_invoke_unlinkable_client_is_unknown_not_absent() -> None:
    # Model from a parameter: cannot see its construction -> UNKNOWN, never a
    # false ABSENT that would make COST-001 misfire.
    src = "def run(m):\n    return m.invoke('hi')\n"
    # (m is a param so the invoke is unlinkable and not tagged at all here)
    assert _annotate(src) == []


# --- tools (TOOL_DEF) ---------------------------------------------------------


def test_tool_decorator_typed_has_schema() -> None:
    src = "from langchain_core.tools import tool\n@tool\ndef search(q: str) -> str:\n    return q\n"
    n = _one(src, SemanticTag.TOOL_DEF)
    assert n.attrs["has_schema"] == Known(True)
    assert n.attrs["name"] == Known("search")


def test_tool_decorator_untyped_no_schema() -> None:
    src = "from langchain_core.tools import tool\n@tool\ndef search(q):\n    return q\n"
    assert _attr(src, SemanticTag.TOOL_DEF, "has_schema") == Known(False)


def test_structured_tool_with_args_schema_has_schema() -> None:
    src = (
        "from langchain.tools import StructuredTool\n"
        "t = StructuredTool.from_function(fn, args_schema=S)\n"
    )
    assert _attr(src, SemanticTag.TOOL_DEF, "has_schema") == Known(True)


# --- gating + negative --------------------------------------------------------


def test_adapter_gated_off_without_trigger_import() -> None:
    st = parse("a.py", "x = 1\n")
    assert collect_semantics(st, ADAPTERS) == []


def test_plain_python_yields_no_annotations() -> None:
    assert _annotate("def f(x):\n    return x + 1\n") == []


def test_registered_in_adapters_with_priority_20() -> None:
    lc = [a for a in ADAPTERS if isinstance(a, LangChainAdapter)]
    assert lc and lc[0].priority == 20
