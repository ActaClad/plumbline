"""JSON reporter — the Finding model serialized (architecture.md §6).

A stable, machine-readable view of the whole scan. Deterministic
(sorted keys, no timestamps) so it is byte-reproducible like SARIF (ADR-0002 D3).
"""

from __future__ import annotations

import json
from typing import Any

from ..engine import ScanResult
from ..model import Finding

JSON_VERSION = 1


def to_json_obj(result: ScanResult) -> dict[str, Any]:
    return {
        "version": JSON_VERSION,
        "findings": [_finding(f) for f in result.findings],
        "suppressed": [
            {**_finding(sf.finding), "suppression": sf.kind} for sf in result.suppressed
        ],
        "analyzer_errors": [
            {"file": e.file, "stage": e.stage, "message": e.message} for e in result.analyzer_errors
        ],
        "gate": {"passed": result.gate.passed, "reasons": list(result.gate.reasons)},
        "summary": {
            "files_scanned": result.files_scanned,
            "rules_loaded": result.rules_loaded,
            "semantic_node_count": result.semantic_node_count,
            "finding_count": len(result.findings),
            "suppressed_count": len(result.suppressed),
        },
    }


def render_json(result: ScanResult) -> str:
    return json.dumps(to_json_obj(result), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(result: ScanResult, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_json(result))


def _finding(f: Finding) -> dict[str, Any]:
    return {
        "rule_id": f.rule_id,
        "title": f.title,
        "category": f.category,
        "pillar": f.pillar.name,
        "severity": f.severity.label,
        "confidence": f.confidence.label,
        "message": f.message,
        "why_it_matters": f.why_it_matters,
        "file": f.file,
        "line": f.line,
        "column": f.column,
        "end_line": f.end_line,
        "snippet": f.snippet,
        "standards": list(f.standards),
        "remediation": f.remediation,
        "fingerprint": f.fingerprint,
    }
