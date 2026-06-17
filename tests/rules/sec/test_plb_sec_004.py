"""PLB-SEC-004 fixtures fire/stay-silent (safe forms must not fire)."""

from __future__ import annotations

from plumbline.rules.sec.plb_sec_004 import RULE
from tests.rules._harness import assert_fixtures, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-SEC-004"
    assert RULE.pillar.name == "SECURITY"


def test_secret_named_heuristic_is_test_path_aware(tmp_path) -> None:
    # A `*_token = "<label>"` that isn't an obvious fake (a contextvar token — the
    # real-repo FP class on crewAI) fires in src but is suppressed in a test file.
    src = 'def t():\n    session_token = "context-var-token"\n'
    (tmp_path / "test_ctx.py").write_text(src)
    (tmp_path / "app.py").write_text(src)
    assert run_file_rule(RULE, tmp_path / "test_ctx.py") == []  # suppressed in tests
    assert [
        f for f in run_file_rule(RULE, tmp_path / "app.py") if f.rule_id == RULE.id
    ]  # src fires
