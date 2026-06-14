"""Skill-pack exporter (ADR-0011).

Serializes the SAME discovered rules (ADR-0005) — metadata, remediation, and the
real bad/good fixtures — into a portable markdown pack a coding tool can read to
*generate* reliable agentic code by default. Author once (the rule module),
render twice (detector + skill).

Mechanical and deterministic (ADR-0011 D2): no LLM, no network, sorted by rule
ID, byte-reproducible like the reporters. The pack is **prevention, never the
gate and never a substitute for the engine** (ADR-0011 D4) — stated in the
emitted SKILL.md.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from ..model import Pillar
from ..rules.base import Rule

PACK_FORMAT = "claude-skill"

_POSITIONING = (
    "> **This pack is prevention, not verification.** It helps a coding tool write "
    "reliable agentic code by default. It is NOT a linter and NOT a CI gate — mistakes "
    "here are cheap because the deterministic Plumbline engine catches them at review "
    "time. Run `plumb scan` for the authoritative, gating check (ADR-0011 D4)."
)


def build_skill_pack(rules: Sequence[Rule], fixtures_root: Path, version: str) -> dict[str, str]:
    """The pack as {relative-path: content}. Deterministic, sorted by rule ID."""
    ordered = sorted(rules, key=lambda r: r.id)
    files: dict[str, str] = {"SKILL.md": _render_index(ordered)}
    for rule in ordered:
        files[f"rules/{rule.id}.md"] = _render_rule(rule, fixtures_root)
    files["manifest.json"] = _render_manifest(ordered, version)
    return files


def write_skill_pack(
    out_dir: Path, rules: Sequence[Rule], fixtures_root: Path, version: str
) -> list[Path]:
    written: list[Path] = []
    for rel, content in build_skill_pack(rules, fixtures_root, version).items():
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #


def _render_index(rules: Sequence[Rule]) -> str:
    lines = [
        "# Plumbline rule pack — write reliable agentic code by default",
        "",
        _POSITIONING,
        "",
        "These rules encode how to build LLM/agent systems that survive production: "
        "bounded loops, timeouts and retries, validated tool I/O, guarded output "
        "parsing, evaluation harnesses, and safe handling of model output. Apply them "
        "while writing code; Plumbline's engine verifies them at review time.",
        "",
    ]
    by_pillar: dict[Pillar, list[Rule]] = {}
    for rule in rules:
        by_pillar.setdefault(rule.pillar, []).append(rule)
    for pillar in Pillar:  # fixed enum order
        group = by_pillar.get(pillar)
        if not group:
            continue
        lines.append(f"## {pillar.display}")
        lines.append("")
        for rule in group:
            lines.append(
                f"- **[{rule.id}](rules/{rule.id}.md)** — {rule.title}: {rule.why_it_matters}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_rule(rule: Rule, fixtures_root: Path) -> str:
    lines = [
        f"# {rule.id} — {rule.title}",
        "",
        f"- **Pillar:** {rule.pillar.display}",
        f"- **Severity / confidence:** {rule.severity.label} / {rule.confidence.label}",
    ]
    if rule.standards:
        lines.append(f"- **Standards:** {', '.join(rule.standards)}")
    lines += ["", "## Why it matters", "", rule.why_it_matters, ""]

    bad = _fixture_example(fixtures_root, rule.id, "bad")
    good = _fixture_example(fixtures_root, rule.id, "good")
    if bad is not None:
        lines += [
            "## Avoid (a real defect this would flag)",
            "",
            "```python",
            bad.rstrip(),
            "```",
            "",
        ]
    if good is not None:
        lines += ["## Prefer", "", "```python", good.rstrip(), "```", ""]

    lines += ["## How to do it right", "", rule.remediation.rstrip(), ""]
    return "\n".join(lines).rstrip() + "\n"


def _render_manifest(rules: Sequence[Rule], version: str) -> str:
    manifest = {
        "format": PACK_FORMAT,
        "package_version": version,
        "rule_count": len(rules),
        "rules": [r.id for r in rules],
    }
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def _fixture_example(fixtures_root: Path, rule_id: str, kind: str) -> str | None:
    """The first `kind` (bad/good) fixture for a rule — a file fixture's
    `kind_*.py`, or a representative `.py` from a `kind_*/` project-fixture
    directory. None if no fixtures are present (e.g. installed without them)."""
    rule_dir = fixtures_root / rule_id
    if not rule_dir.is_dir():
        return None
    files = sorted(rule_dir.glob(f"{kind}_*.py"))
    if files:
        return files[0].read_text(encoding="utf-8")
    for sub in sorted(p for p in rule_dir.glob(f"{kind}_*") if p.is_dir()):
        pys = [p for p in sorted(sub.rglob("*.py")) if p.name != "__init__.py"]
        if pys:
            return pys[0].read_text(encoding="utf-8")
    return None
