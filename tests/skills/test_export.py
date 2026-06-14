"""Skill-pack export tests (ADR-0011) — completeness, determinism, positioning."""

from __future__ import annotations

import json
from pathlib import Path

from plumbline.rules.base import discover_rules
from plumbline.skills.export import build_skill_pack, write_skill_pack

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures"
RULES = discover_rules()


def test_pack_has_a_file_for_every_discovered_rule() -> None:
    pack = build_skill_pack(RULES, FIXTURES, "1.2.3")
    for rule in RULES:
        assert f"rules/{rule.id}.md" in pack
    assert "SKILL.md" in pack and "manifest.json" in pack


def test_manifest_records_version_and_all_rule_ids() -> None:
    pack = build_skill_pack(RULES, FIXTURES, "1.2.3")
    manifest = json.loads(pack["manifest.json"])
    assert manifest["package_version"] == "1.2.3"
    assert manifest["rule_count"] == len(RULES)
    assert manifest["rules"] == sorted(r.id for r in RULES)
    assert manifest["format"] == "claude-skill"


def test_export_is_byte_deterministic() -> None:
    a = build_skill_pack(RULES, FIXTURES, "1.2.3")
    b = build_skill_pack(RULES, FIXTURES, "1.2.3")
    assert a == b


def test_skill_index_states_the_positioning_guardrail() -> None:
    # ADR-0011 D4: the pack must say it is prevention, never the gate.
    skill = build_skill_pack(RULES, FIXTURES, "1.2.3")["SKILL.md"]
    assert "prevention, not verification" in skill
    assert "plumb scan" in skill  # points to the authoritative check


def test_rule_page_embeds_real_fixtures() -> None:
    # RES-001 has file fixtures; its page should carry the bad + good examples.
    page = build_skill_pack(RULES, FIXTURES, "1.2.3")["rules/PLB-RES-001.md"]
    assert "## Avoid" in page and "## Prefer" in page
    assert "```python" in page
    assert "timeout" in page


def test_write_skill_pack_creates_files(tmp_path: Path) -> None:
    written = write_skill_pack(tmp_path, RULES, FIXTURES, "9.9.9")
    assert (tmp_path / "SKILL.md").exists()
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "rules" / "PLB-SEC-002.md").exists()
    assert len(written) == len(RULES) + 2  # per-rule + SKILL.md + manifest.json


def test_no_llm_no_network_marker() -> None:
    # A smoke check that the exporter is pure metadata serialization: building the
    # pack twice from the same inputs is identical (covered above) and it needs
    # only rules + a fixtures path — no client, no key.
    pack = build_skill_pack(RULES, FIXTURES, "1.2.3")
    assert all(isinstance(v, str) for v in pack.values())
