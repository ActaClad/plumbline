"""PLB-SEC-002 — untrusted content executed by eval/exec/compile."""

from __future__ import annotations

from plumbline.rules.sec.plb_sec_002 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-SEC-002"
    assert RULE.pillar.name == "SECURITY"
    assert RULE.severity.label == "Blocker"
    assert "CWE-95" in RULE.standards


def test_finding_carries_source_to_sink_codeflow() -> None:
    findings = run_file_rule(RULE, fixture_dir(RULE) / "bad_eval_llm_output.py")
    f = next(f for f in findings if f.rule_id == RULE.id)
    assert f.code_flow  # witness present
    assert f.code_flow[-1].message.endswith("eval()")  # sink is the last step
    assert "LLM_OUTPUT" in f.code_flow[0].message  # source is first


def test_exec_of_user_input_fires(tmp_path) -> None:
    (tmp_path / "h.py").write_text(
        "from flask import Flask\n"
        "app = Flask(__name__)\n"
        "@app.post('/run')\n"
        "def run(cmd):\n"
        "    return exec(cmd)\n"
    )
    findings = run_file_rule(RULE, tmp_path / "h.py")
    assert [f for f in findings if f.rule_id == RULE.id]
