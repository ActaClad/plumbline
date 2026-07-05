"""Golden tests for the gemini adapter (adapter-contract.md §9b, §6).

Covers the real-repo call shapes that were previously invisible: the current
`google-genai` SDK (client + sync/async `generate_content`, streaming, Live,
embeddings; `from google import genai` and `import google.genai` and
`from google.genai import Client` import styles) and the legacy
`google.generativeai` SDK. The precision contract is asserted too: nested-config
params resolve to UNKNOWN (not ABSENT), so High rules stay silent.
"""

from __future__ import annotations

from plumbline.adapters import ADAPTERS
from plumbline.adapters.base import collect_semantics
from plumbline.adapters.gemini import GeminiAdapter
from plumbline.core.ast_layer import parse
from plumbline.model import UNKNOWN, Known, Resolved, SemanticNode, SemanticTag


def _annotate(src: str) -> list[SemanticNode]:
    return list(GeminiAdapter().annotate(parse("a.py", src)))


def _one(src: str, tag: SemanticTag) -> SemanticNode:
    nodes = [n for n in _annotate(src) if n.tag is tag]
    assert len(nodes) == 1, f"expected exactly one {tag}, got {len(nodes)}"
    return nodes[0]


def _attr(src: str, tag: SemanticTag, key: str) -> Resolved:
    return _one(src, tag).attrs[key]


# --- the primary real-repo shape: from google import genai; client.aio.models --


def test_new_sdk_client_create() -> None:
    src = "from google import genai\nc = genai.Client(api_key='k')\n"
    n = _one(src, SemanticTag.LLM_CLIENT_CREATE)
    assert n.attrs["provider"] == Known("google")


def test_sync_generate_content_is_llm_call() -> None:
    src = (
        "from google import genai\n"
        "c = genai.Client(api_key='k')\n"
        "r = c.models.generate_content(model='gemini-2.0-flash', contents='hi')\n"
    )
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("gemini-2.0-flash")


def test_async_aio_generate_content_is_llm_call() -> None:
    # The exact voice-agent shape: `await client.aio.models.generate_content(...)`.
    src = (
        "from google import genai\n"
        "c = genai.Client(api_key='k')\n"
        "async def f():\n"
        "    return await c.aio.models.generate_content(model='gemini-1.5-pro', contents='x')\n"
    )
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("gemini-1.5-pro")


def test_generate_content_stream_is_llm_call() -> None:
    src = (
        "from google import genai\n"
        "c = genai.Client()\n"
        "for chunk in c.models.generate_content_stream(model='gemini-2.0-flash', contents='x'):\n"
        "    pass\n"
    )
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("gemini-2.0-flash")


def test_live_connect_is_llm_call() -> None:
    # The Gemini Live (voice) path — makes the telephony modules visible.
    src = (
        "from google import genai\n"
        "c = genai.Client()\n"
        "async def f():\n"
        "    async with c.aio.live.connect(model='gemini-2.0-flash-live') as s:\n"
        "        pass\n"
    )
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("gemini-2.0-flash-live")


def test_embed_content_is_embedding_call() -> None:
    src = (
        "from google import genai\n"
        "c = genai.Client()\n"
        "e = c.models.embed_content(model='text-embedding-004', contents='x')\n"
    )
    assert _attr(src, SemanticTag.EMBEDDING_CALL, "model") == Known("text-embedding-004")


# --- import-style variants ---------------------------------------------------


def test_import_google_genai_as_alias() -> None:
    src = (
        "import google.genai as g\n"
        "c = g.Client()\n"
        "r = c.models.generate_content(model='gemini-2.0-flash', contents='x')\n"
    )
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("gemini-2.0-flash")
    assert any(n.tag is SemanticTag.LLM_CLIENT_CREATE for n in _annotate(src))


def test_from_google_genai_import_client() -> None:
    src = (
        "from google.genai import Client\n"
        "c = Client()\n"
        "r = c.models.generate_content(model='gemini-2.0-flash', contents='x')\n"
    )
    assert any(n.tag is SemanticTag.LLM_CLIENT_CREATE for n in _annotate(src))
    assert _attr(src, SemanticTag.LLM_CALL, "model") == Known("gemini-2.0-flash")


# --- legacy google.generativeai ----------------------------------------------


def test_legacy_generative_model_and_generate_content() -> None:
    src = (
        "import google.generativeai as genai\n"
        "m = genai.GenerativeModel('gemini-pro')\n"
        "r = m.generate_content('hi')\n"
    )
    assert any(n.tag is SemanticTag.LLM_CLIENT_CREATE for n in _annotate(src))
    assert len([n for n in _annotate(src) if n.tag is SemanticTag.LLM_CALL]) == 1


def test_bare_generate_content_ignored_without_legacy_import() -> None:
    # A `.generate_content` on some non-Gemini object must NOT be tagged when no
    # Gemini SDK is imported in the file (avoids a false LLM_CALL).
    src = "import google.cloud.storage\nx.generate_content('hi')\n"
    assert [n for n in _annotate(src) if n.tag is SemanticTag.LLM_CALL] == []


# --- precision contract: nested config is UNKNOWN, not ABSENT ----------------


def test_nested_config_params_are_unknown_not_absent() -> None:
    # timeout/max_tokens/tools live inside config=/http_options -> UNKNOWN so the
    # High RES/COST rules do NOT fire (they'd false-positive on ABSENT here).
    src = (
        "from google import genai\n"
        "c = genai.Client()\n"
        "r = c.models.generate_content(model='gemini-2.0-flash', contents='x',\n"
        "    config=genai.types.GenerateContentConfig(max_output_tokens=256))\n"
    )
    n = _one(src, SemanticTag.LLM_CALL)
    assert n.attrs["timeout"] is UNKNOWN
    assert n.attrs["max_tokens"] is UNKNOWN
    assert n.attrs["tools"] is UNKNOWN


# --- gating & registration ---------------------------------------------------


def test_gated_off_without_google_import() -> None:
    st = parse("a.py", "x = 1\nc.models.generate_content(model='m', contents='x')\n")
    assert collect_semantics(st, ADAPTERS) == []


def test_registered_with_priority_15_per_file() -> None:
    g = [a for a in ADAPTERS if isinstance(a, GeminiAdapter)]
    assert g and g[0].priority == 15 and g[0].project_triggered is False
