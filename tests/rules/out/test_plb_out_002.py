"""PLB-OUT-002 — LLM output used directly as control flow."""

from __future__ import annotations

from plumbline.rules.out.plb_out_002 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-OUT-002"
    assert RULE.category == "OUT"
    assert RULE.pillar.display.startswith("Reliability")
    assert RULE.severity.label == "Major"
    assert RULE.confidence.label == "Medium"


def test_empty_guard_is_not_flagged() -> None:
    # `if not out:` is the recommended empty-output guard, not the defect.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_empty_guard.py") == []


def test_membership_validation_is_not_flagged() -> None:
    # `if x in ALLOWED:` is the validation fix, not raw equality branching.
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_membership_validation.py") == []


def test_structured_envelope_dispatch_is_not_flagged() -> None:
    # `if item.type == "function_call":` is schema dispatch on a discriminator
    # field, not content-branching — the real-repo FP class (simonw/llm).
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_structured_dispatch.py") == []


def test_finding_carries_taint_witness() -> None:
    d = fixture_dir(RULE)
    fired = [f for f in run_file_rule(RULE, d / "bad_equality_branch.py") if f.rule_id == RULE.id]
    assert fired
    assert fired[0].code_flow, "OUT-002 should emit a source->sink taint witness"
