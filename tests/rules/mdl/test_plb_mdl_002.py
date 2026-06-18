"""PLB-MDL-002 — deprecated / sunset model identifier."""

from __future__ import annotations

from plumbline.data.deprecated_models import DEPRECATED_MODELS
from plumbline.rules.mdl.plb_mdl_002 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-MDL-002"
    assert RULE.category == "MDL"
    assert RULE.severity.label == "Critical"
    # Ships advisory until a real-repo precision pass (ADR-0017), NOT High.
    assert RULE.confidence.label == "Medium"


def test_current_model_is_not_flagged() -> None:
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_current_model.py") == []


def test_deprecated_via_variable_is_caught() -> None:
    # Resolved through a single-assignment constant, not an inline literal.
    d = fixture_dir(RULE)
    fired = [
        f for f in run_file_rule(RULE, d / "bad_deprecated_via_variable.py") if f.rule_id == RULE.id
    ]
    assert fired


def test_data_table_is_exact_ids_only() -> None:
    # Guard the precision invariant (ADR-0017): no empty keys, no whitespace —
    # exact-match against a live model id must never accidentally hit.
    for model_id in DEPRECATED_MODELS:
        assert model_id == model_id.strip() and model_id, f"bad id {model_id!r}"
    assert "gpt-4o" not in DEPRECATED_MODELS
    assert "gpt-4o-mini" not in DEPRECATED_MODELS
