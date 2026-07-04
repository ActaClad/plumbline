"""PLB-MDL-008 — OpenAI reasoning model uses max_tokens not max_completion_tokens."""

from __future__ import annotations

from plumbline.data.reasoning_models import OPENAI_REASONING_MODELS
from plumbline.rules.mdl.plb_mdl_008 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-MDL-008"
    assert RULE.severity.label == "Critical"
    assert RULE.confidence.label == "Medium"  # advisory until benchmarked (ADR-0018)


def test_anthropic_max_tokens_is_silent() -> None:
    # Anthropic REQUIRES max_tokens — flagging it would be a false positive.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_claude_max_tokens.py") == []


def test_openai_reasoning_set_excludes_chat_models() -> None:
    # Chat models legitimately take max_tokens; they must not be in the set.
    assert "gpt-4o" not in OPENAI_REASONING_MODELS
    assert "gpt-4o-mini" not in OPENAI_REASONING_MODELS
    assert "o3" in OPENAI_REASONING_MODELS
