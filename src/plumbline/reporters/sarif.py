"""SARIF 2.1.0 reporter (ADR-0006).

Output validates against the vendored SARIF 2.1.0 schema (tested) and is
byte-reproducible — no timestamps (ADR-0002 D3, ADR-0006 D3). Emits driver
rules, results, locations, fingerprints, suppressions, analyzer-error
notifications, and — for taint rules — source→sink `codeFlows` (ADR-0014).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from .. import __version__
from ..engine import ScanResult
from ..model import Confidence, Finding, Pillar, Severity, finding_sort_key
from ..rules.base import Rule
from ..scoring import compute_scores

SARIF_SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"
_INFORMATION_URI = "https://github.com/actaclad/plumbline"
_CATALOG_URI = "https://github.com/actaclad/plumbline/blob/main/docs/specs/rule-catalog.md"

_LEVEL: dict[Severity, str] = {
    Severity.BLOCKER: "error",
    Severity.CRITICAL: "error",
    Severity.MAJOR: "warning",
    Severity.MINOR: "note",
    Severity.INFO: "note",
}
_RANK: dict[Confidence, float] = {
    Confidence.HIGH: 90.0,
    Confidence.MEDIUM: 50.0,
    Confidence.LOW: 10.0,
}


def to_sarif(result: ScanResult, rules: Sequence[Rule]) -> dict[str, Any]:
    """Build the SARIF log as a plain dict (deterministic key/element order)."""
    ordered_rules = sorted(rules, key=lambda r: r.id)
    rule_index = {r.id: i for i, r in enumerate(ordered_rules)}

    driver_rules = [_rule_descriptor(r) for r in ordered_rules]
    # Active and suppressed findings are both emitted as results; suppressed ones
    # carry a `suppressions` array (ADR-0006). Sort the union for determinism.
    rows: list[tuple[Finding, str | None]] = [(f, None) for f in result.findings]
    rows += [(sf.finding, sf.kind) for sf in result.suppressed]
    rows.sort(key=lambda row: finding_sort_key(row[0]))
    results = [_result(f, rule_index, suppression=kind) for f, kind in rows]
    notifications = [_notification(e.file, e.stage, e.message) for e in result.analyzer_errors]

    invocation: dict[str, Any] = {"executionSuccessful": True}
    if notifications:
        invocation["toolExecutionNotifications"] = notifications

    scores = compute_scores(result.findings, result.semantic_node_count)
    run_props: dict[str, Any] = {
        "plumbline/scoringModel": scores.model,
        "plumbline/readinessScore": scores.readiness,  # null when N/A (ADR-0008 D3)
        "plumbline/pillarScores": {
            p.name: (scores.pillars.get(p) if scores.applicable else None) for p in Pillar
        },
    }

    return {
        "$schema": SARIF_SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Plumbline",
                        "informationUri": _INFORMATION_URI,
                        "semanticVersion": __version__,
                        "rules": driver_rules,
                    }
                },
                "columnKind": "unicodeCodePoints",
                "originalUriBaseIds": {"SRCROOT": {"uri": "file:///"}},
                "invocations": [invocation],
                "properties": run_props,
                "results": results,
            }
        ],
    }


def write_sarif(result: ScanResult, rules: Sequence[Rule], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_sarif(result, rules))


def render_sarif(result: ScanResult, rules: Sequence[Rule]) -> str:
    # Sorted keys + trailing newline => byte-stable output.
    return json.dumps(to_sarif(result, rules), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _rule_descriptor(rule: Rule) -> dict[str, Any]:
    props: dict[str, Any] = {
        "plumbline/pillar": rule.pillar.name,
        "plumbline/severity": rule.severity.label,
        "plumbline/confidence": rule.confidence.label,
        "tags": [*rule.standards, rule.pillar.display],
    }
    if rule.pillar is Pillar.SECURITY:
        props["security-severity"] = _security_severity(rule.severity)
    return {
        "id": rule.id,
        "name": _slug(rule.title),
        "shortDescription": {"text": rule.title},
        "fullDescription": {"text": rule.why_it_matters},
        "help": {"text": rule.remediation},
        "helpUri": f"{_CATALOG_URI}#{rule.id.lower()}",
        "defaultConfiguration": {"level": _LEVEL[rule.severity]},
        "properties": props,
    }


def _result(
    finding: Finding, rule_index: dict[str, int], *, suppression: str | None = None
) -> dict[str, Any]:
    region: dict[str, Any] = {"startLine": finding.line}
    if finding.column is not None:
        region["startColumn"] = finding.column + 1  # SARIF is 1-based (ADR-0006 D3)
    if finding.end_line is not None:
        region["endLine"] = finding.end_line
    result: dict[str, Any] = {
        "ruleId": finding.rule_id,
        "level": _LEVEL[finding.severity],
        "rank": _RANK[finding.confidence],
        "message": {"text": finding.message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": finding.file, "uriBaseId": "SRCROOT"},
                    "region": region,
                }
            }
        ],
        "partialFingerprints": {"plumblineFingerprint/v1": finding.fingerprint},
        "properties": {
            "plumbline/severity": finding.severity.label,
            "plumbline/confidence": finding.confidence.label,
        },
    }
    if finding.rule_id in rule_index:
        result["ruleIndex"] = rule_index[finding.rule_id]
    if finding.code_flow:
        result["codeFlows"] = _code_flows(finding)
    if suppression is not None:
        result["suppressions"] = [{"kind": suppression}]
    return result


def _code_flows(finding: Finding) -> list[dict[str, Any]]:
    """One codeFlow / threadFlow, source→sink in `code_flow` order (ADR-0014 D3)."""
    locations = []
    for step in finding.code_flow:
        region: dict[str, Any] = {"startLine": step.line}
        if step.column is not None:
            region["startColumn"] = step.column + 1  # SARIF is 1-based
        locations.append(
            {
                "location": {
                    "physicalLocation": {
                        "artifactLocation": {"uri": step.file, "uriBaseId": "SRCROOT"},
                        "region": region,
                    },
                    "message": {"text": step.message},
                }
            }
        )
    return [{"threadFlows": [{"locations": locations}]}]


def _notification(file: str, stage: str, message: str) -> dict[str, Any]:
    return {
        "level": "error",
        "message": {"text": f"[{stage}] {message}"},
        "locations": [{"physicalLocation": {"artifactLocation": {"uri": file}}}],
    }


def _security_severity(severity: Severity) -> str:
    return {
        Severity.BLOCKER: "9.0",
        Severity.CRITICAL: "8.0",
        Severity.MAJOR: "5.0",
        Severity.MINOR: "3.0",
        Severity.INFO: "1.0",
    }[severity]


def _slug(title: str) -> str:
    return "".join(c if c.isalnum() else "" for c in title.title())
