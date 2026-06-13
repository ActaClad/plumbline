"""Golden tests for the openai_sdk adapter (adapter-contract.md §5/§6)."""

from __future__ import annotations

from plumbline.adapters import ADAPTERS
from plumbline.adapters.base import SemanticIndex, collect_semantics
from plumbline.adapters.openai_sdk import OpenAISDKAdapter
from plumbline.core.ast_layer import parse
from plumbline.model import ABSENT, UNKNOWN, Known, Resolved, SemanticNode, SemanticTag


def _annotate(src: str) -> list[SemanticNode]:
    st = parse("a.py", src)
    return list(OpenAISDKAdapter().annotate(st))


def _one(src: str, tag: SemanticTag) -> SemanticNode:
    nodes = [n for n in _annotate(src) if n.tag is tag]
    assert len(nodes) == 1, f"expected exactly one {tag}, got {len(nodes)}"
    return nodes[0]


def _attr(src: str, tag: SemanticTag, key: str) -> Resolved:
    return _one(src, tag).attrs[key]


# --- client construction ------------------------------------------------------


def test_openai_client_create_detected() -> None:
    n = _one("from openai import OpenAI\nc = OpenAI()\n", SemanticTag.LLM_CLIENT_CREATE)
    assert n.attrs["provider"] == Known("openai")


def test_anthropic_client_create_detected() -> None:
    n = _one("from anthropic import Anthropic\nc = Anthropic()\n", SemanticTag.LLM_CLIENT_CREATE)
    assert n.attrs["provider"] == Known("anthropic")


def test_module_style_import_client_create() -> None:
    n = _one("import openai\nc = openai.OpenAI()\n", SemanticTag.LLM_CLIENT_CREATE)
    assert n.attrs["provider"] == Known("openai")


def test_async_client_create() -> None:
    n = _one("from openai import AsyncOpenAI\nc = AsyncOpenAI()\n", SemanticTag.LLM_CLIENT_CREATE)
    assert n.attrs["provider"] == Known("openai")


# --- LLM_CALL classification --------------------------------------------------


def test_chat_completions_create_is_llm_call() -> None:
    src = "from openai import OpenAI\nc = OpenAI()\nc.chat.completions.create(model='gpt-4o')\n"
    n = _one(src, SemanticTag.LLM_CALL)
    assert n.attrs["model"] == Known("gpt-4o")


def test_anthropic_messages_create_is_llm_call() -> None:
    src = "from anthropic import Anthropic\nc = Anthropic()\nc.messages.create(model='claude')\n"
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("claude")


def test_responses_create_is_llm_call() -> None:
    src = "from openai import OpenAI\nc = OpenAI()\nc.responses.create(model='gpt-4o')\n"
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("gpt-4o")


def test_embeddings_create_is_embedding_call() -> None:
    src = "from openai import OpenAI\nc = OpenAI()\nc.embeddings.create(model='te-3')\n"
    assert _attr(src, SemanticTag.EMBEDDING_CALL, "model") == Known("te-3")


# --- timeout resolution + provenance (ADR-0004 D3, adapter-contract §4.3/§5) --


def test_no_timeout_anywhere_falls_back_to_sdk_default() -> None:
    src = "from openai import OpenAI\nc = OpenAI()\nc.chat.completions.create(model='m')\n"
    n = _one(src, SemanticTag.LLM_CALL)
    assert n.attrs["timeout"] == Known(600.0)
    assert n.attrs["timeout_source"] == Known("sdk_default")


def test_timeout_on_client_is_resolved() -> None:
    src = (
        "from openai import OpenAI\n"
        "c = OpenAI(timeout=30)\n"
        "c.chat.completions.create(model='m')\n"
    )
    n = _one(src, SemanticTag.LLM_CALL)
    assert n.attrs["timeout"] == Known(30)
    assert n.attrs["timeout_source"] == Known("client")


def test_timeout_on_call_wins() -> None:
    src = (
        "from openai import OpenAI\n"
        "c = OpenAI(timeout=30)\n"
        "c.chat.completions.create(model='m', timeout=5)\n"
    )
    n = _one(src, SemanticTag.LLM_CALL)
    assert n.attrs["timeout"] == Known(5)
    assert n.attrs["timeout_source"] == Known("explicit")


def test_timeout_explicitly_none_is_known_none() -> None:
    # Explicitly disabling the timeout is the unbounded case PLB-RES-001 targets.
    src = (
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "c.chat.completions.create(model='m', timeout=None)\n"
    )
    n = _one(src, SemanticTag.LLM_CALL)
    assert n.attrs["timeout"] == Known(None)
    assert n.attrs["timeout_source"] == Known("explicit")


def test_timeout_unresolvable_is_unknown() -> None:
    src = (
        "from openai import OpenAI\n"
        "import cfg\n"
        "c = OpenAI()\n"
        "c.chat.completions.create(model='m', timeout=cfg.T)\n"
    )
    assert _attr(src, SemanticTag.LLM_CALL, "timeout") is UNKNOWN


def test_unresolvable_client_yields_unknown_timeout_not_sdk_default() -> None:
    # Client comes from a parameter -> provider unknown -> cannot claim a default.
    src = (
        "from openai import OpenAI\n"
        "def f(c):\n"
        "    c.chat.completions.create(model='m')\n"
    )
    assert _attr(src, SemanticTag.LLM_CALL, "timeout") is UNKNOWN


def test_client_in_module_scope_links_from_function_call() -> None:
    src = (
        "from openai import OpenAI\n"
        "c = OpenAI(timeout=30)\n"
        "def f():\n"
        "    return c.chat.completions.create(model='m')\n"
    )
    n = _one(src, SemanticTag.LLM_CALL)
    assert n.attrs["timeout"] == Known(30)


# --- gating + determinism -----------------------------------------------------


def test_adapter_gated_off_without_trigger_import() -> None:
    st = parse("a.py", "x = 1\n")
    assert collect_semantics(st, ADAPTERS) == []


def test_collect_semantics_runs_when_triggered() -> None:
    st = parse("a.py", "from openai import OpenAI\nc = OpenAI()\n")
    nodes = collect_semantics(st, ADAPTERS)
    assert any(n.tag is SemanticTag.LLM_CLIENT_CREATE for n in nodes)


def test_semantic_index_by_tag_is_sorted() -> None:
    src = (
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "c.chat.completions.create(model='a')\n"
        "c.chat.completions.create(model='b')\n"
    )
    idx = SemanticIndex(_annotate(src))
    calls = idx.by_tag(SemanticTag.LLM_CALL)
    lines = [getattr(n.node, "lineno") for n in calls]  # noqa: B009
    assert lines == sorted(lines)


def test_plain_python_yields_no_annotations() -> None:
    assert _annotate("def f(x):\n    return x + 1\n") == []


def test_attrs_default_to_absent_or_unknown_not_missing() -> None:
    src = "from openai import OpenAI\nc = OpenAI()\nc.chat.completions.create(model='m')\n"
    n = _one(src, SemanticTag.LLM_CALL)
    # temperature absent at call level -> ABSENT (no client merge for call-level params)
    assert n.attrs["temperature"] is ABSENT
