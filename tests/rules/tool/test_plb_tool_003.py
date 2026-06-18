"""PLB-TOOL-003 — tool with no error handling can crash the agent run."""

from __future__ import annotations

from plumbline.rules.tool.plb_tool_003 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-TOOL-003"
    assert RULE.category == "TOOL"
    assert RULE.severity.label == "Major"
    assert RULE.confidence.label == "Medium"  # advisory — never gates


def test_guarded_tool_does_not_fire() -> None:
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_langchain_guarded_http.py") == []


def test_pure_computation_does_not_fire() -> None:
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_pure_computation.py") == []


def test_tools_in_test_files_are_not_flagged(tmp_path) -> None:
    src = (
        "from langchain_core.tools import tool\n"
        "import requests\n\n"
        "@tool\n"
        "def fetch(url: str) -> str:\n"
        "    return requests.get(url).text\n"
    )
    (tmp_path / "test_tools.py").write_text(src)
    (tmp_path / "tools.py").write_text(src)
    assert run_file_rule(RULE, tmp_path / "test_tools.py") == []  # suppressed
    assert [f for f in run_file_rule(RULE, tmp_path / "tools.py") if f.rule_id == RULE.id]
