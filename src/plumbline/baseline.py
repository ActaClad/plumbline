"""Baseline file load/write (ADR-0006 D5).

A baseline is the set of accepted finding fingerprints. Matching is by
fingerprint only; `rule_id`/`file` are human-readable context. Baselined
findings are reported-but-suppressed: excluded from the gate and scoring.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .model import Finding

BASELINE_VERSION = 1
FINGERPRINT_ALGORITHM = "v1"  # must match ADR-0002 D2 / SARIF partialFingerprints key


class BaselineError(Exception):
    """A malformed or incompatible baseline file (CLI maps to exit 2)."""


def load_baseline_fingerprints(path: Path) -> frozenset[str]:
    """Return the accepted fingerprints from a baseline file, or empty if absent."""
    if not path.is_file():
        return frozenset()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"{path}: invalid baseline file ({exc})") from exc
    algorithm = data.get("algorithm")
    if algorithm != FINGERPRINT_ALGORITHM:
        raise BaselineError(
            f"{path}: baseline algorithm {algorithm!r} != {FINGERPRINT_ALGORITHM!r}; "
            f"regenerate with `plumb baseline`"
        )
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        raise BaselineError(f"{path}: 'findings' must be a list")
    return frozenset(str(f["fingerprint"]) for f in findings if "fingerprint" in f)


def render_baseline(findings: Sequence[Finding]) -> str:
    """Serialize findings into a deterministic baseline document."""
    entries: list[dict[str, Any]] = [
        {"fingerprint": f.fingerprint, "rule_id": f.rule_id, "file": f.file}
        for f in sorted(findings, key=lambda f: (f.fingerprint, f.rule_id, f.file))
    ]
    doc = {"version": BASELINE_VERSION, "algorithm": FINGERPRINT_ALGORITHM, "findings": entries}
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_baseline(path: Path, findings: Sequence[Finding]) -> None:
    path.write_text(render_baseline(findings), encoding="utf-8")
