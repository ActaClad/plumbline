"""PLB-MDL-006 — removed sampling param on a reasoning model."""

from __future__ import annotations

from plumbline.data.reasoning_models import SAMPLING_UNSUPPORTED
from plumbline.rules.mdl.plb_mdl_006 import RULE
from tests.rules._harness import assert_fixtures, fixture_dir, run_file_rule


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-MDL-006"
    assert RULE.category == "MDL"
    assert RULE.severity.label == "Critical"
    # Ships advisory until a real-repo precision pass (ADR-0018), NOT High.
    assert RULE.confidence.label == "Medium"
    assert "CWE-628" in RULE.standards


def test_reasoning_model_via_variable_is_caught() -> None:
    # claude-opus-4-8 pinned in a single-assignment constant, resolved like MDL-002.
    d = fixture_dir(RULE)
    fired = [f for f in run_file_rule(RULE, d / "bad_claude_opus_top_p.py") if f.rule_id == RULE.id]
    assert fired
    assert "top_p" in fired[0].message


def test_chat_model_with_temperature_is_silent() -> None:
    # The rule keys on the model, not the mere presence of a sampling param —
    # temperature on gpt-4o is valid code and must never fire (precision boundary).
    d = fixture_dir(RULE)
    assert run_file_rule(RULE, d / "good_gpt4o_temperature.py") == []


def test_data_table_is_exact_ids_only() -> None:
    # Precision invariant (ADR-0017/0018): exact, non-empty ids; never a live
    # chat model that legitimately accepts sampling params.
    for model_id, params in SAMPLING_UNSUPPORTED.items():
        assert model_id == model_id.strip() and model_id, f"bad id {model_id!r}"
        assert params, f"{model_id!r} maps to no params"
    assert "gpt-4o" not in SAMPLING_UNSUPPORTED
    assert "gpt-4o-mini" not in SAMPLING_UNSUPPORTED
