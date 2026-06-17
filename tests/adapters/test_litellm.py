"""Golden tests for the litellm adapter (adapter-contract.md §9a, §6)."""

from __future__ import annotations

from plumbline.adapters import ADAPTERS
from plumbline.adapters.base import collect_semantics
from plumbline.adapters.litellm import LiteLLMAdapter
from plumbline.core.ast_layer import parse
from plumbline.model import ABSENT, Known, Resolved, SemanticNode, SemanticTag


def _annotate(src: str) -> list[SemanticNode]:
    return list(LiteLLMAdapter().annotate(parse("a.py", src)))


def _one(src: str, tag: SemanticTag) -> SemanticNode:
    nodes = [n for n in _annotate(src) if n.tag is tag]
    assert len(nodes) == 1, f"expected exactly one {tag}, got {len(nodes)}"
    return nodes[0]


def _attr(src: str, tag: SemanticTag, key: str) -> Resolved:
    return _one(src, tag).attrs[key]


def test_module_style_completion_is_llm_call() -> None:
    src = "import litellm\nlitellm.completion(model='gpt-4o', messages=[])\n"
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("gpt-4o")


def test_from_import_completion_is_llm_call() -> None:
    src = "from litellm import completion\ncompletion(model='claude-3', messages=[])\n"
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("claude-3")


def test_aliased_completion_resolves() -> None:
    src = "from litellm import completion as c\nc(model='m', messages=[])\n"
    assert _one(src, SemanticTag.LLM_CALL).attrs["model"] == Known("m")


def test_embedding_is_embedding_call() -> None:
    src = "import litellm\nlitellm.embedding(model='text-embedding-3', input='x')\n"
    assert _attr(src, SemanticTag.EMBEDDING_CALL, "model") == Known("text-embedding-3")


def test_explicit_timeout_none_is_known_none() -> None:
    # The unbounded case RES-001 targets — fires cross-framework via the same tag.
    src = "import litellm\nlitellm.completion(model='m', messages=[], timeout=None)\n"
    assert _attr(src, SemanticTag.LLM_CALL, "timeout") == Known(None)


def test_explicit_num_retries_zero_maps_to_max_retries() -> None:
    # LiteLLM's num_retries -> normalized max_retries (RES-002 reads max_retries).
    src = "import litellm\nlitellm.completion(model='m', messages=[], num_retries=0)\n"
    assert _attr(src, SemanticTag.LLM_CALL, "max_retries") == Known(0)


def test_bare_call_claims_no_defaults() -> None:
    # No timeout/num_retries/max_tokens on a bare call -> ABSENT, not a forced
    # default (so RES-001/002 stay silent; COST-001 correctly sees uncapped tokens).
    src = "import litellm\nlitellm.completion(model='m', messages=[])\n"
    n = _one(src, SemanticTag.LLM_CALL)
    assert n.attrs["timeout"] is ABSENT
    assert n.attrs["max_retries"] is ABSENT
    assert n.attrs["max_tokens"] is ABSENT


def test_gated_off_without_litellm_import() -> None:
    st = parse("a.py", "x = 1\ncompletion(model='m')\n")
    assert collect_semantics(st, ADAPTERS) == []


def test_registered_with_priority_15() -> None:
    ll = [a for a in ADAPTERS if isinstance(a, LiteLLMAdapter)]
    assert ll and ll[0].priority == 15 and ll[0].project_triggered is False
