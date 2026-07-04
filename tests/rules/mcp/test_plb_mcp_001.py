"""PLB-MCP-001 — remote MCP server with no authentication."""

from __future__ import annotations

from plumbline.rules.mcp.plb_mcp_001 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-MCP-001"
    assert RULE.category == "MCP"
    assert RULE.pillar.name == "SECURITY"
    assert RULE.severity.label == "Critical"
    assert RULE.confidence.label == "Medium"  # advisory: middleware/proxy auth FP vector
    assert "CWE-306" in RULE.standards


def test_stdio_is_silent() -> None:
    # Default stdio transport is local, not network-exposed.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_stdio_local.py") == []


def test_loopback_is_silent() -> None:
    # A remote transport bound to loopback is not exposed.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_loopback_bound.py") == []


def test_auth_configured_is_silent() -> None:
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_remote_with_auth.py") == []
