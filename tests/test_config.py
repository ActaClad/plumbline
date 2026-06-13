"""Tests for config loading, strict validation, and the Quality Gate (ADR-0007)."""

from __future__ import annotations

from pathlib import Path

import pytest

from plumbline.config import (
    EXAMPLE_TOML,
    Config,
    ConfigError,
    GateConfig,
    evaluate_gate,
    load_config,
    parse_config,
)
from plumbline.model import (
    Confidence,
    Finding,
    Pillar,
    Severity,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _finding(rule_id: str, severity: Severity, confidence: Confidence) -> Finding:
    return Finding(
        rule_id=rule_id,
        title="t",
        category="RES",
        pillar=Pillar.RELIABILITY,
        severity=severity,
        confidence=confidence,
        message="m",
        why_it_matters="w",
        file="a.py",
        line=1,
        column=0,
        end_line=None,
        snippet=None,
        standards=(),
        remediation="r",
        fingerprint="0",
    )


# --- example lock (ADR-0007 D2) ----------------------------------------------


def test_example_file_matches_canonical_constant() -> None:
    example = (REPO_ROOT / ".plumbline.toml.example").read_text()
    assert example == EXAMPLE_TOML, "regenerate .plumbline.toml.example from config.EXAMPLE_TOML"


def test_example_parses_to_defaults() -> None:
    assert parse_config(EXAMPLE_TOML) == Config()


# --- defaults ----------------------------------------------------------------


def test_empty_config_is_defaults() -> None:
    cfg = parse_config("")
    assert cfg == Config()
    assert cfg.gate.fail_on_severity == (Severity.BLOCKER,)
    assert cfg.gate.fail_on_high_confidence_severity == (Severity.CRITICAL,)


# --- strict validation (ADR-0007 D3) -----------------------------------------


def test_unknown_section_is_error() -> None:
    with pytest.raises(ConfigError, match="unknown key 'scna'"):
        parse_config("[scna]\n")


def test_unknown_key_suggests_correction() -> None:
    with pytest.raises(ConfigError, match="did you mean 'include'"):
        parse_config("[scan]\ninclud = ['.']\n")


def test_unknown_severity_is_error() -> None:
    with pytest.raises(ConfigError, match="unknown severity 'Blokcer'"):
        parse_config("[gate]\nfail_on_severity = ['Blokcer']\n")


def test_malformed_rule_id_is_error() -> None:
    with pytest.raises(ConfigError, match="malformed rule id"):
        parse_config("[rules]\ndisabled = ['RES-001']\n")


def test_unknown_output_format_is_error() -> None:
    with pytest.raises(ConfigError, match="unknown format 'xml'"):
        parse_config("[output]\nformats = ['xml']\n")


def test_wrong_type_is_error() -> None:
    with pytest.raises(ConfigError, match="expected true/false"):
        parse_config("[scan]\nrespect_gitignore = 'yes'\n")


def test_invalid_toml_is_error() -> None:
    with pytest.raises(ConfigError, match="invalid TOML"):
        parse_config("[scan\n")


# --- valid overrides ---------------------------------------------------------


def test_severity_override_parsed() -> None:
    cfg = parse_config('[rules]\n[rules.severity_override]\n"PLB-COST-001" = "Minor"\n')
    assert cfg.rules.severity_override == {"PLB-COST-001": Severity.MINOR}


def test_rule_param_table_parsed() -> None:
    cfg = parse_config('[rules.params."PLB-MDL-003"]\ntemperature_threshold = 0.3\n')
    assert cfg.rules.params["PLB-MDL-003"]["temperature_threshold"] == 0.3


# --- validate_against_rules --------------------------------------------------


def test_override_referencing_unknown_rule_is_error() -> None:
    cfg = parse_config("[rules]\ndisabled = ['PLB-RES-999']\n")
    with pytest.raises(ConfigError, match="unknown rule 'PLB-RES-999'"):
        cfg.validate_against_rules(frozenset({"PLB-RES-001"}))


def test_known_rule_reference_passes() -> None:
    cfg = parse_config("[rules]\ndisabled = ['PLB-RES-001']\n")
    cfg.validate_against_rules(frozenset({"PLB-RES-001"}))  # no raise


# --- precedence (ADR-0007 D1) ------------------------------------------------


def test_dotfile_takes_precedence_and_notices_pyproject(tmp_path: Path) -> None:
    (tmp_path / ".plumbline.toml").write_text("[gate]\nfail_on_severity = ['Major']\n")
    (tmp_path / "pyproject.toml").write_text("[tool.plumbline.gate]\nfail_on_severity = ['Info']\n")
    loaded = load_config(tmp_path)
    assert loaded.config.gate.fail_on_severity == (Severity.MAJOR,)
    assert any("using .plumbline.toml" in n for n in loaded.notices)


def test_pyproject_used_when_no_dotfile(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.plumbline.gate]\nfail_on_severity = ['Info']\n")
    loaded = load_config(tmp_path)
    assert loaded.config.gate.fail_on_severity == (Severity.INFO,)


def test_defaults_when_nothing_present(tmp_path: Path) -> None:
    loaded = load_config(tmp_path)
    assert loaded.config == Config()
    assert loaded.source is None


def test_explicit_missing_path_is_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no such file"):
        load_config(tmp_path, explicit_path=tmp_path / "nope.toml")


# --- Quality Gate (ADR-0007 D5) ----------------------------------------------


def test_gate_passes_with_no_findings() -> None:
    assert evaluate_gate([], GateConfig()).passed


def test_gate_fails_on_blocker_any_confidence() -> None:
    v = evaluate_gate([_finding("PLB-RES-001", Severity.BLOCKER, Confidence.LOW)], GateConfig())
    assert not v.passed
    assert "PLB-RES-001" in v.reasons[0]


def test_gate_fails_on_high_confidence_critical() -> None:
    v = evaluate_gate([_finding("PLB-X-001", Severity.CRITICAL, Confidence.HIGH)], GateConfig())
    assert not v.passed


def test_gate_passes_on_medium_confidence_critical() -> None:
    # Critical only gates at High confidence by default.
    v = evaluate_gate([_finding("PLB-X-001", Severity.CRITICAL, Confidence.MEDIUM)], GateConfig())
    assert v.passed


def test_gate_passes_on_major() -> None:
    v = evaluate_gate([_finding("PLB-X-001", Severity.MAJOR, Confidence.HIGH)], GateConfig())
    assert v.passed
