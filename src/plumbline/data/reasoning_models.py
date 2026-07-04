"""Reasoning/thinking-model call-contract tables (ADR-0017, ADR-0018).

Manually-curated static snapshots — not a live feed — consumed by the MDL-006/
007/008 reasoning-config rules. Matched by **exact** model-id string equality
against a call's resolved `model=` value, so entries must be full, exact
identifiers (precision over recall: a partial/prefix match could flag a model
that does not actually reject the param — a false positive on working code).

The bar for adding an id is "provably rejects the param," never "looks like a
reasoning model." A missing id is a recall gap (safe); a wrong id is a false
positive (not). Keeping these current is a maintenance task tracked in
`docs/backlog.md`.

Last reviewed: 2026-07.

Sources: OpenAI reasoning guide (o-series/GPT-5 reject sampling params and require
`max_completion_tokens`); Anthropic model docs + the bundled `claude-api`
migration guide (Opus 4.7/4.8 and Fable-5 removed `temperature`/`top_p`/`top_k`).
"""

from __future__ import annotations

# OpenAI reasoning models: the API has no `top_k`; `temperature`/`top_p` are
# rejected outright on these models.
_OPENAI_SAMPLING = frozenset({"temperature", "top_p"})
# Anthropic reasoning models (4.7+/Fable): sampling params removed entirely.
_ANTHROPIC_SAMPLING = frozenset({"temperature", "top_p", "top_k"})

#: Exact model id -> the sampling params that return HTTP 400 if passed.
#: Consumed by PLB-MDL-006.
SAMPLING_UNSUPPORTED: dict[str, frozenset[str]] = {
    # --- OpenAI o-series (reasoning) -----------------------------------------
    "o1": _OPENAI_SAMPLING,
    "o1-mini": _OPENAI_SAMPLING,
    "o1-preview": _OPENAI_SAMPLING,
    "o1-pro": _OPENAI_SAMPLING,
    "o3": _OPENAI_SAMPLING,
    "o3-mini": _OPENAI_SAMPLING,
    "o3-pro": _OPENAI_SAMPLING,
    "o4-mini": _OPENAI_SAMPLING,
    # --- OpenAI GPT-5 (reasoning) --------------------------------------------
    "gpt-5": _OPENAI_SAMPLING,
    "gpt-5-mini": _OPENAI_SAMPLING,
    "gpt-5-nano": _OPENAI_SAMPLING,
    # --- Anthropic Opus 4.7/4.8 + Fable-5 (sampling params removed) ----------
    "claude-opus-4-7": _ANTHROPIC_SAMPLING,
    "claude-opus-4-8": _ANTHROPIC_SAMPLING,
    "claude-fable-5": _ANTHROPIC_SAMPLING,
}

#: OpenAI reasoning models that reject `max_tokens` and require
#: `max_completion_tokens` on Chat Completions (HTTP 400 otherwise).
#: Consumed by PLB-MDL-008. Anthropic models are intentionally absent — they
#: *require* `max_tokens`, so flagging it there would be a false positive.
OPENAI_REASONING_MODELS: frozenset[str] = frozenset(
    {
        "o1",
        "o1-mini",
        "o1-preview",
        "o1-pro",
        "o3",
        "o3-mini",
        "o3-pro",
        "o4-mini",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
    }
)
