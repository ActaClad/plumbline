"""PLB-MDL-003 — high temperature on a tool-calling / agentic path."""

from __future__ import annotations

from plumbline.rules.mdl.plb_mdl_003 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-MDL-003"
    assert RULE.category == "MDL"
    assert RULE.pillar.display.startswith("Reliability")
    assert RULE.severity.label == "Major"
    assert RULE.confidence.label == "Medium"  # advisory — never gates


def test_low_temperature_tool_call_is_silent() -> None:
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_low_temp_tool_call.py") == []


def test_high_temperature_without_tools_is_silent() -> None:
    # No tools = creative generation, where higher temperature is appropriate.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_high_temp_no_tools.py") == []
