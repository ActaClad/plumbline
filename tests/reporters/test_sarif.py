"""SARIF reporter tests — schema validity + determinism (ADR-0006)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from plumbline.config import Config
from plumbline.engine import scan
from plumbline.reporters.sarif import render_sarif, to_sarif
from plumbline.rules.base import discover_rules

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO_ROOT / "tests" / "data" / "sarif-2.1.0.json").read_text())
RULES = discover_rules()


def _scan_with_finding(tmp_path: Path) -> object:
    (tmp_path / "agent.py").write_text(
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        # max_tokens set so only RES-001 fires (one finding to assert on).
        "c.chat.completions.create(model='m', timeout=None, max_tokens=256)\n"
    )
    # Harness evidence so EVAL-001/OBS-001 (project-scope) stay silent.
    (tmp_path / "_harness.py").write_text("import deepeval\nimport opentelemetry\n")
    return scan(tmp_path, Config(), RULES)


def test_sarif_validates_against_schema_with_findings(tmp_path: Path) -> None:
    result = _scan_with_finding(tmp_path)
    sarif = to_sarif(result, RULES)  # type: ignore[arg-type]
    jsonschema.validate(sarif, SCHEMA)  # raises on invalid


def test_sarif_validates_against_schema_empty(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    result = scan(tmp_path, Config(), RULES)
    jsonschema.validate(to_sarif(result, RULES), SCHEMA)  # type: ignore[arg-type]


def test_sarif_contains_finding_with_fingerprint(tmp_path: Path) -> None:
    result = _scan_with_finding(tmp_path)
    sarif = to_sarif(result, RULES)  # type: ignore[arg-type]
    results = sarif["runs"][0]["results"]
    assert len(results) == 1
    r = results[0]
    assert r["ruleId"] == "PLB-RES-001"
    assert r["level"] == "error"  # Blocker -> error
    assert r["partialFingerprints"]["plumblineFingerprint/v1"]
    assert r["locations"][0]["physicalLocation"]["region"]["startLine"] == 3


def test_driver_lists_all_loaded_rules(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    sarif = to_sarif(scan(tmp_path, Config(), RULES), RULES)  # type: ignore[arg-type]
    rule_ids = {r["id"] for r in sarif["runs"][0]["tool"]["driver"]["rules"]}
    assert "PLB-RES-001" in rule_ids


def test_analyzer_error_becomes_notification_not_failed_run(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def f(:\n")
    result = scan(tmp_path, Config(), RULES)
    sarif = to_sarif(result, RULES)  # type: ignore[arg-type]
    invocation = sarif["runs"][0]["invocations"][0]
    assert invocation["executionSuccessful"] is True
    assert invocation["toolExecutionNotifications"][0]["level"] == "error"
    jsonschema.validate(sarif, SCHEMA)


def test_sarif_is_byte_deterministic(tmp_path: Path) -> None:
    result = _scan_with_finding(tmp_path)
    assert render_sarif(result, RULES) == render_sarif(result, RULES)  # type: ignore[arg-type]


def test_no_timestamps_emitted(tmp_path: Path) -> None:
    # Byte-reproducibility forbids timestamps (ADR-0006 D3).
    text = render_sarif(_scan_with_finding(tmp_path), RULES)  # type: ignore[arg-type]
    assert "endTimeUtc" not in text and "startTimeUtc" not in text


def test_taint_finding_emits_codeflows(tmp_path: Path) -> None:
    # OUT-001 is a taint rule; its witness must surface as schema-valid codeFlows
    # (ADR-0014). source (LLM_OUTPUT) -> sink (json.loads).
    (tmp_path / "a.py").write_text(
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "import json\n"
        "r = c.chat.completions.create(model='m', timeout=5, max_tokens=10)\n"
        "data = json.loads(r.choices[0].message.content)\n"
    )
    result = scan(tmp_path, Config(), RULES)
    sarif = to_sarif(result, RULES)  # type: ignore[arg-type]
    jsonschema.validate(sarif, SCHEMA)
    out = next(r for r in sarif["runs"][0]["results"] if r["ruleId"] == "PLB-OUT-001")
    steps = out["codeFlows"][0]["threadFlows"][0]["locations"]
    assert len(steps) >= 2  # at least source + sink
    assert steps[-1]["location"]["message"]["text"] == "parsed by json.loads()"


def test_codeflow_sarif_is_byte_deterministic(tmp_path: Path) -> None:
    # The codeFlows array is an ordered list (not key-sorted by json.dumps), so
    # its determinism is a distinct invariant from the witness-free path
    # (ADR-0002 D3). Render a code_flow-bearing SARIF twice; assert byte-equal.
    (tmp_path / "a.py").write_text(
        "from openai import OpenAI\n"
        "c = OpenAI()\n"
        "import json\n"
        "r = c.chat.completions.create(model='m', timeout=5, max_tokens=10)\n"
        "data = json.loads(r.choices[0].message.content)\n"
    )
    result = scan(tmp_path, Config(), RULES)
    assert render_sarif(result, RULES) == render_sarif(result, RULES)  # type: ignore[arg-type]
