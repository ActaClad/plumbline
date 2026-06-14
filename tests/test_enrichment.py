"""AI remediation enrichment — the determinism firewall (ADR-0015, CLAUDE.md §1.1).

No test touches the network: a FakeEnricher stands in for the LLM.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from plumbline.config import AIConfig, Config
from plumbline.engine import scan
from plumbline.enrichment import build_enricher, enrich_result
from plumbline.model import Finding
from plumbline.rules.base import discover_rules

RULES = discover_rules()


class FakeEnricher:
    """Returns DIFFERENT remediation text for every finding — the whole point is
    to prove that even when the AI changes everything it can, detection is
    untouched."""

    def enrich(self, finding: Finding) -> str | None:
        return f"AI-TAILORED fix for {finding.rule_id} at {finding.file}:{finding.line}"


class NullEnricher:
    def enrich(self, finding: Finding) -> str | None:
        return None


def _project(tmp_path: Path) -> Path:
    (tmp_path / "agent.py").write_text(
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "c.chat.completions.create(model='m', timeout=None, max_tokens=10)\n"
    )
    (tmp_path / "_h.py").write_text("import deepeval\nimport opentelemetry\n")
    return tmp_path


def test_enrichment_cannot_alter_detection(tmp_path: Path) -> None:
    base = scan(_project(tmp_path), Config(), RULES)
    enriched = enrich_result(base, FakeEnricher())

    # The §1.1 contract: gate verdict + reasons identical (the CI mechanism).
    assert enriched.gate == base.gate
    assert enriched.analyzer_errors == base.analyzer_errors
    assert enriched.semantic_node_count == base.semantic_node_count
    assert len(enriched.findings) == len(base.findings) >= 1

    for b, e in zip(base.findings, enriched.findings, strict=True):
        # Every detection field is byte-identical...
        assert (b.fingerprint, b.severity, b.confidence, b.file, b.line, b.pillar, b.rule_id) == (
            e.fingerprint,
            e.severity,
            e.confidence,
            e.file,
            e.line,
            e.pillar,
            e.rule_id,
        )
        # ...only the remediation text and its label changed.
        assert e.remediation != b.remediation
        assert e.remediation_is_ai is True
        assert b.remediation_is_ai is False


def test_null_enricher_keeps_static_remediation(tmp_path: Path) -> None:
    base = scan(_project(tmp_path), Config(), RULES)
    out = enrich_result(base, NullEnricher())
    for b, o in zip(base.findings, out.findings, strict=True):
        assert o.remediation == b.remediation
        assert o.remediation_is_ai is False


def test_off_by_default_builds_no_enricher() -> None:
    enricher, notice = build_enricher(Config())
    assert enricher is None
    assert notice is None  # off -> silent


def test_enabled_but_unavailable_returns_notice_not_silence(monkeypatch) -> None:
    # Enabled with no key / no SDK -> no enricher, but the user is told (D3).
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = dataclasses.replace(Config(), ai=AIConfig(enrich_remediation=True))
    enricher, notice = build_enricher(cfg)
    assert enricher is None
    assert notice is not None and "static remediation" in notice


def test_enricher_error_degrades_to_static(tmp_path: Path) -> None:
    class Boom:
        def enrich(self, finding: Finding) -> str | None:
            raise RuntimeError("LLM down")

    base = scan(_project(tmp_path), Config(), RULES)
    out = enrich_result(base, Boom())  # must not raise
    for b, o in zip(base.findings, out.findings, strict=True):
        assert o.remediation == b.remediation
        assert o.remediation_is_ai is False
