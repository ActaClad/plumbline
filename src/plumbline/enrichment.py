"""AI-assisted remediation enrichment (ADR-0015) — the ONLY place an LLM enters.

This module is never imported by `engine.scan()` or any detector. It runs in the
CLI *after* a final `ScanResult` is produced, and may rewrite a finding's
`remediation` text and nothing else. Detection, fingerprints, and the gate are
untouched by construction (CLAUDE.md §1.1).

The provider SDK is the optional `[ai]` extra, lazy-imported inside the enricher
so the package imports and runs without it. No code here is exercised by the
default (AI-off) path, and no test touches the network.
"""

from __future__ import annotations

import dataclasses
import os
from typing import Protocol, runtime_checkable

from .config import Config
from .engine import ScanResult
from .model import Finding

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_API_KEY_ENV = "ANTHROPIC_API_KEY"


@runtime_checkable
class Enricher(Protocol):
    """Rewrites one finding's remediation text. Returns None to keep the static
    text (e.g. on an API error) — enrichment must degrade, never fail the scan."""

    def enrich(self, finding: Finding) -> str | None: ...


def enrich_result(result: ScanResult, enricher: Enricher) -> ScanResult:
    """Return a new ScanResult with AI-rewritten remediation on active findings.

    Pure: only `remediation`/`remediation_is_ai` change; `gate`, `suppressed`,
    `analyzer_errors`, and every detection field are carried through unchanged
    (ADR-0015 D1 — the gate is NEVER recomputed here)."""
    findings = tuple(_enrich_one(f, enricher) for f in result.findings)
    return dataclasses.replace(result, findings=findings)


def _enrich_one(finding: Finding, enricher: Enricher) -> Finding:
    try:
        text = enricher.enrich(finding)
    except Exception:  # noqa: BLE001 — a flaky LLM must never break the report
        text = None
    if not text or text == finding.remediation:
        return finding
    return dataclasses.replace(finding, remediation=text, remediation_is_ai=True)


def build_enricher(config: Config) -> tuple[Enricher | None, str | None]:
    """Construct the configured enricher, or (None, notice).

    Returns (None, None) when enrichment is off. When it is enabled but cannot
    run — the `[ai]` extra is missing, or no API key — returns (None, notice):
    detection and exit code are identical to disabled, but the user is told
    (ADR-0015 D3), never silently downgraded."""
    if not config.ai.enrich_remediation:
        return None, None
    try:
        import anthropic  # noqa: F401 — lazy: only when AI is enabled
    except ImportError:
        return None, (
            "AI enrichment is enabled but the 'ai' extra is not installed "
            "(pip install actaclad-plumbline[ai]); using static remediation."
        )
    key = os.environ.get(_API_KEY_ENV)
    if not key:
        return None, (
            f"AI enrichment is enabled but {_API_KEY_ENV} is not set; using static remediation."
        )
    return AnthropicEnricher(api_key=key), None


class AnthropicEnricher:
    """Tailors a finding's generic remediation to its specific code via Claude.

    Lazy-imports the SDK in __init__; never reachable unless AI is enabled and a
    key is present. It is handed only the finding (already decided) — it cannot
    influence whether the finding exists."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def enrich(self, finding: Finding) -> str | None:
        prompt = _PROMPT.format(
            rule=finding.rule_id,
            title=finding.title,
            message=finding.message,
            snippet=(finding.snippet or "").strip() or "(snippet unavailable)",
            remediation=finding.remediation.strip(),
        )
        # This is the deliberate AI boundary — our one LLM call, rewriting only
        # remediation text (never gating). Its output is not eval-gated, so
        # suppress EVAL-001 here (dogfooding our own inline-suppression mechanism).
        resp = self._client.messages.create(  # plumb: ignore[PLB-EVAL-001]
            model=self._model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in resp.content if getattr(block, "type", "") == "text"]
        text = "".join(parts).strip()
        return text or None


_PROMPT = """\
You are helping a developer fix a static-analysis finding. Rewrite the generic
remediation below as concrete, specific guidance for THIS code. Keep it short
(a few lines), actionable, and do not restate the problem. Output only the fix.

Rule: {rule} — {title}
Finding: {message}
Code:
{snippet}

Generic remediation:
{remediation}
"""
