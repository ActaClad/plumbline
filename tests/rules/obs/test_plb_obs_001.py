"""PLB-OBS-001 — no tracing/instrumentation configured (project-scope)."""

from __future__ import annotations

from plumbline.rules.obs.plb_obs_001 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_project_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-OBS-001"
    assert RULE.scope.value == "project"
    assert RULE.confidence.label == "Medium"


def test_finding_discloses_env_var_blind_spot() -> None:
    # The advisor's point: tracing is often enabled via env vars the analyzer
    # can't see — the finding must say so, not pretend it's a clean signal.
    fired = run_project_rule(RULE, fixture_dir(RULE) / "bad_no_tracing")
    msg = next(f.message for f in fired if f.rule_id == RULE.id)
    assert "env var" in msg


def test_otel_import_counts_as_tracing() -> None:
    assert run_project_rule(RULE, fixture_dir(RULE) / "good_with_tracing") == []


def test_env_var_reference_in_code_silences(tmp_path) -> None:
    # An in-code reference to LANGCHAIN_TRACING_V2 shows intent -> silent.
    (tmp_path / "app.py").write_text(
        "import os\n"
        "from openai import OpenAI\n"
        "os.environ['LANGCHAIN_TRACING_V2'] = 'true'\n"
        "c = OpenAI()\n"
        "c.chat.completions.create(model='m', timeout=5, max_tokens=10)\n"
    )
    assert run_project_rule(RULE, tmp_path) == []
