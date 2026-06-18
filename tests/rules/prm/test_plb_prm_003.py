"""PLB-PRM-003 — no system prompt defined."""

from __future__ import annotations

from plumbline.rules.prm.plb_prm_003 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-PRM-003"
    assert RULE.category == "PRM"
    assert RULE.pillar.display.startswith("Architecture")
    assert RULE.severity.label == "Minor"
    assert RULE.confidence.label == "Medium"


def test_anthropic_system_kwarg_is_recognized() -> None:
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_anthropic_system_kwarg.py") == []


def test_opaque_messages_are_not_guessed() -> None:
    # messages passed as a variable -> roles not visible -> never fire.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_opaque_messages.py") == []
