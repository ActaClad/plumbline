"""PLB-TOOL-001 — tool without an input schema / typed signature."""

from __future__ import annotations

from plumbline.rules.tool.plb_tool_001 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-TOOL-001"
    assert RULE.category == "TOOL"
    assert RULE.severity.label == "Major"


def test_fires_on_langchain_and_crewai_untyped_tools() -> None:
    d = fixture_dir(RULE)
    for bad in ("bad_langchain_untyped.py", "bad_crewai_untyped.py"):
        fired = [f for f in run_file_rule(RULE, d / bad) if f.rule_id == RULE.id]
        assert fired, f"expected TOOL-001 to fire on {bad}"


def test_typed_tool_does_not_fire() -> None:
    assert run_file_rule(RULE, fixture_dir(RULE) / "good_langchain_typed.py") == []


def test_crewai_basetool_schema_mechanisms_recognized() -> None:
    # The crewAI FP class: schema declared in __init__ or via a typed _run, not as
    # a class-body args_schema attr. Both good; the no-schema one still fires.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_crewai_init_schema.py") == []
    assert run_file_rule(RULE, d / "good_crewai_typed_run.py") == []
    assert [f for f in run_file_rule(RULE, d / "bad_crewai_no_schema.py") if f.rule_id == RULE.id]


def test_tools_in_test_files_are_not_flagged(tmp_path) -> None:
    # Tools defined in tests are scaffolding (real-repo FPs: crewAI's test suite).
    src = "from langchain_core.tools import tool\n@tool\ndef helper(x):\n    return x\n"
    (tmp_path / "test_tools.py").write_text(src)
    (tmp_path / "tools.py").write_text(src)
    assert run_file_rule(RULE, tmp_path / "test_tools.py") == []  # suppressed in tests
    assert [f for f in run_file_rule(RULE, tmp_path / "tools.py") if f.rule_id == RULE.id]  # src
