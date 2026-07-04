"""PLB-MCP-003 — over-broad / wildcard MCP OAuth scopes."""

from __future__ import annotations

from plumbline.rules.mcp.plb_mcp_003 import RULE, _is_broad
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-MCP-003"
    assert RULE.category == "MCP"
    assert RULE.pillar.name == "SECURITY"
    assert RULE.confidence.label == "Medium"


def test_broadness_classifier() -> None:
    for broad in ("*", "admin:*", "files:*", "full-access", "ALL"):
        assert _is_broad(broad), broad
    for ok in ("weather:read", "user:profile", "read", "write:notes"):
        assert not _is_broad(ok), ok


def test_minimal_scopes_silent() -> None:
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_minimal_scopes.py") == []
