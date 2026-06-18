"""Deprecated / sunset model identifiers (ADR-0017) — consumed by PLB-MDL-002.

A **manually-curated static snapshot**, not a live feed. It is matched by exact
string equality against a call's resolved `model=` value, so it must list full,
exact identifiers (precision over recall — a partial/prefix match would flag
live models like `gpt-4o`). Each value is a short human note: when it was
retired/deprecated and what to migrate to.

Last reviewed: 2026-06. Keeping this current is a maintenance task, not an
automated one — the refresh process is tracked in `docs/backlog.md`. As long as
every entry is a genuinely-retired id, the list can only go stale in the *safe*
direction (a missed deprecation is a recall gap, never a false positive) — so the
bar for *adding* an id is "provably retired/sunset," never "looks old": a
wrongly-listed live model would be a flat false positive on working code.

Sources: OpenAI and Anthropic public model-deprecation pages. Only identifiers
that are unambiguously retired or on a published sunset path are included.
"""

from __future__ import annotations

#: Exact model id -> short deprecation note (when retired; suggested migration).
DEPRECATED_MODELS: dict[str, str] = {
    # --- OpenAI: GPT-3 base + InstructGPT (retired 2024-01-04) ----------------
    "ada": "retired 2024-01-04; migrate to gpt-4o-mini",
    "babbage": "retired 2024-01-04; migrate to gpt-4o-mini",
    "curie": "retired 2024-01-04; migrate to gpt-4o-mini",
    "davinci": "retired 2024-01-04; migrate to gpt-4o",
    "text-ada-001": "retired 2024-01-04; migrate to gpt-4o-mini",
    "text-babbage-001": "retired 2024-01-04; migrate to gpt-4o-mini",
    "text-curie-001": "retired 2024-01-04; migrate to gpt-4o-mini",
    "text-davinci-001": "retired 2024-01-04; migrate to gpt-4o",
    "text-davinci-002": "retired 2024-01-04; migrate to gpt-4o",
    "text-davinci-003": "retired 2024-01-04; migrate to gpt-4o",
    "code-davinci-002": "retired 2023-03; migrate to gpt-4o",
    "code-cushman-001": "retired 2023-03; migrate to gpt-4o-mini",
    # --- OpenAI: dated chat snapshots that have been sunset -------------------
    "gpt-3.5-turbo-0301": "deprecated; migrate to gpt-4o-mini",
    "gpt-3.5-turbo-0613": "deprecated; migrate to gpt-4o-mini",
    "gpt-3.5-turbo-16k-0613": "deprecated; migrate to gpt-4o-mini",
    "gpt-4-0314": "deprecated; migrate to gpt-4o",
    "gpt-4-32k-0314": "deprecated; migrate to gpt-4o",
    "gpt-4-vision-preview": "deprecated preview; migrate to gpt-4o",
    "gpt-4-1106-vision-preview": "deprecated preview; migrate to gpt-4o",
    # --- Anthropic: Claude 1 / 2 / Instant (retired) -------------------------
    "claude-1": "retired; migrate to a current Claude model",
    "claude-1.0": "retired; migrate to a current Claude model",
    "claude-1.3": "retired; migrate to a current Claude model",
    "claude-instant-1": "retired; migrate to a current Claude model",
    "claude-instant-1.1": "retired; migrate to a current Claude model",
    "claude-instant-1.2": "retired; migrate to a current Claude model",
    "claude-2": "retired; migrate to a current Claude model",
    "claude-2.0": "retired; migrate to a current Claude model",
    "claude-2.1": "retired; migrate to a current Claude model",
    "claude-3-sonnet-20240229": "retired 2025-07; migrate to a current Claude model",
}
