"""Configuration loading, validation, and the Quality Gate (ADR-0007).

Strict by design: an unrecognized key or a bad value is an error, not a warning
(ADR-0007 D3) — a silently ignored typo in `fail_on_severity` is a silently
disabled CI gate. Parsing uses stdlib `tomllib` (requires-python >= 3.11). No
runtime dependency; no Pydantic (ADR-0007 D4).
"""

from __future__ import annotations

import difflib
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Final, final

from .model import Confidence, Finding, Severity

# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class ConfigError(Exception):
    """Invalid configuration. The CLI maps this to exit code 2 (ADR-0007 D5)."""


# --------------------------------------------------------------------------- #
# Severity name parsing (config speaks labels like "Blocker", model speaks enum)
# --------------------------------------------------------------------------- #

_SEVERITY_BY_LABEL: Final[Mapping[str, Severity]] = {s.label: s for s in Severity}
_VALID_FORMATS: Final[frozenset[str]] = frozenset({"cli", "sarif", "json", "html"})


def _parse_severity(label: str, *, where: str) -> Severity:
    try:
        return _SEVERITY_BY_LABEL[label]
    except KeyError:
        sev = _suggest(label, _SEVERITY_BY_LABEL.keys())
        raise ConfigError(f"{where}: unknown severity {label!r}{sev}") from None


def _suggest(value: str, options: Iterable[object]) -> str:
    matches = difflib.get_close_matches(value, [str(o) for o in options], n=1)
    return f" (did you mean {matches[0]!r}?)" if matches else ""


# --------------------------------------------------------------------------- #
# Config dataclasses (frozen, immutable)
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class ScanConfig:
    include: tuple[str, ...] = (".",)
    exclude: tuple[str, ...] = ()
    respect_gitignore: bool = True
    default_excludes: bool = True


@final
@dataclass(frozen=True, slots=True)
class GateConfig:
    fail_on_severity: tuple[Severity, ...] = (Severity.BLOCKER,)
    fail_on_high_confidence_severity: tuple[Severity, ...] = (Severity.CRITICAL,)


@final
@dataclass(frozen=True, slots=True)
class RulesConfig:
    disabled: frozenset[str] = frozenset()
    severity_override: Mapping[str, Severity] = field(default_factory=dict)
    params: Mapping[str, Mapping[str, object]] = field(default_factory=dict)


@final
@dataclass(frozen=True, slots=True)
class BaselineConfig:
    file: str = ".plumbline-baseline.json"


@final
@dataclass(frozen=True, slots=True)
class OutputConfig:
    formats: tuple[str, ...] = ("cli",)
    sarif_path: str = "plumbline.sarif"
    json_path: str = "plumbline.json"
    html_path: str = "plumbline.html"


@final
@dataclass(frozen=True, slots=True)
class AIConfig:
    enrich_remediation: bool = False


@final
@dataclass(frozen=True, slots=True)
class Config:
    scan: ScanConfig = field(default_factory=ScanConfig)
    gate: GateConfig = field(default_factory=GateConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    baseline: BaselineConfig = field(default_factory=BaselineConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    ai: AIConfig = field(default_factory=AIConfig)

    def validate_against_rules(self, known_rule_ids: frozenset[str]) -> None:
        """Cross-check rule references against the discovered rule set (ADR-0007 D3).

        Called by the engine once rules are loaded — config load alone cannot
        know which rule IDs exist.
        """
        referenced = set(self.rules.disabled) | set(self.rules.severity_override)
        for rule_id in sorted(referenced):
            if rule_id not in known_rule_ids:
                hint = _suggest(rule_id, known_rule_ids)
                raise ConfigError(f"[rules]: override references unknown rule {rule_id!r}{hint}")


@final
@dataclass(frozen=True, slots=True)
class ConfigLoad:
    """Result of loading: the config, where it came from, and any notices."""

    config: Config
    source: str | None
    notices: tuple[str, ...]


# --------------------------------------------------------------------------- #
# Parsing the raw TOML table into a validated Config
# --------------------------------------------------------------------------- #

_RULE_ID_LEN: Final = 3  # PLB-<CAT>-<NNN> -> 3 dash-separated parts after split


def _require_keys(table: Mapping[str, object], allowed: Sequence[str], *, where: str) -> None:
    for key in table:
        if key not in allowed:
            raise ConfigError(f"{where}: unknown key {key!r}{_suggest(key, allowed)}")


def _as_str_tuple(value: object, *, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{where}: expected a list of strings")
    return tuple(value)


def _as_bool(value: object, *, where: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{where}: expected true/false")
    return value


def _as_str(value: object, *, where: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{where}: expected a string")
    return value


def _validate_rule_id(rule_id: str, *, where: str) -> None:
    parts = rule_id.split("-")
    if len(parts) != _RULE_ID_LEN or parts[0] != "PLB" or not parts[2].isdigit():
        raise ConfigError(f"{where}: malformed rule id {rule_id!r} (expected PLB-<CAT>-<NNN>)")


def _build_config(raw: Mapping[str, object]) -> Config:
    _require_keys(raw, ["scan", "gate", "rules", "baseline", "output", "ai"], where="config")
    cfg = Config()

    if (scan := raw.get("scan")) is not None:
        cfg = replace(cfg, scan=_build_scan(_table(scan, where="scan")))
    if (gate := raw.get("gate")) is not None:
        cfg = replace(cfg, gate=_build_gate(_table(gate, where="gate")))
    if (rules := raw.get("rules")) is not None:
        cfg = replace(cfg, rules=_build_rules(_table(rules, where="rules")))
    if (baseline := raw.get("baseline")) is not None:
        cfg = replace(cfg, baseline=_build_baseline(_table(baseline, where="baseline")))
    if (output := raw.get("output")) is not None:
        cfg = replace(cfg, output=_build_output(_table(output, where="output")))
    if (ai := raw.get("ai")) is not None:
        cfg = replace(cfg, ai=_build_ai(_table(ai, where="ai")))
    return cfg


def _table(value: object, *, where: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ConfigError(f"[{where}]: expected a table")
    return value


def _build_scan(t: Mapping[str, object]) -> ScanConfig:
    _require_keys(t, ["include", "exclude", "respect_gitignore", "default_excludes"], where="scan")
    d = ScanConfig()
    return ScanConfig(
        include=_as_str_tuple(t["include"], where="scan.include") if "include" in t else d.include,
        exclude=_as_str_tuple(t["exclude"], where="scan.exclude") if "exclude" in t else d.exclude,
        respect_gitignore=_as_bool(t["respect_gitignore"], where="scan.respect_gitignore")
        if "respect_gitignore" in t
        else d.respect_gitignore,
        default_excludes=_as_bool(t["default_excludes"], where="scan.default_excludes")
        if "default_excludes" in t
        else d.default_excludes,
    )


def _build_gate(t: Mapping[str, object]) -> GateConfig:
    _require_keys(t, ["fail_on_severity", "fail_on_high_confidence_severity"], where="gate")
    d = GateConfig()
    fos = d.fail_on_severity
    if "fail_on_severity" in t:
        labels = _as_str_tuple(t["fail_on_severity"], where="gate.fail_on_severity")
        fos = tuple(_parse_severity(s, where="gate.fail_on_severity") for s in labels)
    fohcs = d.fail_on_high_confidence_severity
    if "fail_on_high_confidence_severity" in t:
        labels = _as_str_tuple(
            t["fail_on_high_confidence_severity"], where="gate.fail_on_high_confidence_severity"
        )
        fohcs = tuple(
            _parse_severity(s, where="gate.fail_on_high_confidence_severity") for s in labels
        )
    return GateConfig(fail_on_severity=fos, fail_on_high_confidence_severity=fohcs)


def _build_rules(t: Mapping[str, object]) -> RulesConfig:
    _require_keys(t, ["disabled", "severity_override", "params"], where="rules")
    disabled: frozenset[str] = frozenset()
    if "disabled" in t:
        ids = _as_str_tuple(t["disabled"], where="rules.disabled")
        for rid in ids:
            _validate_rule_id(rid, where="rules.disabled")
        disabled = frozenset(ids)

    overrides: dict[str, Severity] = {}
    if "severity_override" in t:
        ov = _table(t["severity_override"], where="rules.severity_override")
        for rid, label in ov.items():
            _validate_rule_id(rid, where="rules.severity_override")
            overrides[rid] = _parse_severity(
                _as_str(label, where=f"rules.severity_override.{rid}"),
                where=f"rules.severity_override.{rid}",
            )

    params: dict[str, Mapping[str, object]] = {}
    if "params" in t:
        p = _table(t["params"], where="rules.params")
        for rid, body in p.items():
            _validate_rule_id(rid, where="rules.params")
            params[rid] = _table(body, where=f"rules.params.{rid}")

    return RulesConfig(disabled=disabled, severity_override=overrides, params=params)


def _build_baseline(t: Mapping[str, object]) -> BaselineConfig:
    _require_keys(t, ["file"], where="baseline")
    d = BaselineConfig()
    return BaselineConfig(file=_as_str(t["file"], where="baseline.file") if "file" in t else d.file)


def _build_output(t: Mapping[str, object]) -> OutputConfig:
    _require_keys(t, ["formats", "sarif_path", "json_path", "html_path"], where="output")
    d = OutputConfig()
    formats = d.formats
    if "formats" in t:
        formats = _as_str_tuple(t["formats"], where="output.formats")
        for fmt in formats:
            if fmt not in _VALID_FORMATS:
                raise ConfigError(
                    f"output.formats: unknown format {fmt!r}{_suggest(fmt, _VALID_FORMATS)}"
                )
    return OutputConfig(
        formats=formats,
        sarif_path=_as_str(t["sarif_path"], where="output.sarif_path")
        if "sarif_path" in t
        else d.sarif_path,
        json_path=_as_str(t["json_path"], where="output.json_path")
        if "json_path" in t
        else d.json_path,
        html_path=_as_str(t["html_path"], where="output.html_path")
        if "html_path" in t
        else d.html_path,
    )


def _build_ai(t: Mapping[str, object]) -> AIConfig:
    _require_keys(t, ["enrich_remediation"], where="ai")
    d = AIConfig()
    return AIConfig(
        enrich_remediation=_as_bool(t["enrich_remediation"], where="ai.enrich_remediation")
        if "enrich_remediation" in t
        else d.enrich_remediation
    )


def parse_config(text: str) -> Config:
    """Parse and validate a `.plumbline.toml` document into a Config."""
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML: {exc}") from exc
    return _build_config(raw)


# --------------------------------------------------------------------------- #
# Loading with precedence (ADR-0007 D1)
# --------------------------------------------------------------------------- #


def load_config(scan_root: Path, explicit_path: Path | None = None) -> ConfigLoad:
    """Resolve config by precedence: explicit path > ./.plumbline.toml >
    pyproject [tool.plumbline] > defaults. If both file forms exist, the
    standalone file wins wholesale and a notice names the ignored one.
    """
    notices: list[str] = []

    if explicit_path is not None:
        if not explicit_path.is_file():
            raise ConfigError(f"--config: no such file: {explicit_path}")
        return ConfigLoad(parse_config(explicit_path.read_text()), str(explicit_path), ())

    dotfile = scan_root / ".plumbline.toml"
    pyproject = scan_root / "pyproject.toml"
    pyproject_has_table = _pyproject_has_plumbline(pyproject)

    if dotfile.is_file():
        if pyproject_has_table:
            notices.append(
                "both .plumbline.toml and [tool.plumbline] exist; using .plumbline.toml"
            )
        return ConfigLoad(parse_config(dotfile.read_text()), str(dotfile), tuple(notices))

    if pyproject_has_table:
        raw = tomllib.loads(pyproject.read_text())
        tool = raw.get("tool")
        table = tool.get("plumbline") if isinstance(tool, dict) else None
        return ConfigLoad(_build_config(_table(table, where="tool.plumbline")), str(pyproject), ())

    return ConfigLoad(Config(), None, ())


def _pyproject_has_plumbline(pyproject: Path) -> bool:
    if not pyproject.is_file():
        return False
    try:
        raw = tomllib.loads(pyproject.read_text())
    except tomllib.TOMLDecodeError:
        return False
    tool = raw.get("tool")
    return isinstance(tool, dict) and "plumbline" in tool


# --------------------------------------------------------------------------- #
# Quality Gate (ADR-0007 D5, ADR-0001 D5)
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class GateVerdict:
    passed: bool
    reasons: tuple[str, ...]


def evaluate_gate(findings: Sequence[Finding], gate: GateConfig) -> GateVerdict:
    """Default: fail on any Blocker (any confidence), or any High-confidence
    Critical. `findings` must already exclude suppressed findings (ADR-0006).
    """
    fail_any = set(gate.fail_on_severity)
    fail_high = set(gate.fail_on_high_confidence_severity)
    reasons: list[str] = []
    for f in findings:
        if f.severity in fail_any:
            reasons.append(f"{f.rule_id} ({f.severity.label}) at {f.file}:{f.line}")
        elif f.severity in fail_high and f.confidence is Confidence.HIGH:
            reasons.append(
                f"{f.rule_id} ({f.severity.label}, High confidence) at {f.file}:{f.line}"
            )
    return GateVerdict(passed=not reasons, reasons=tuple(reasons))


# --------------------------------------------------------------------------- #
# Canonical example. The uncommented values are EXACTLY the defaults, so a test
# asserts both that `.plumbline.toml.example` equals this string and that
# parsing it yields `Config()` — docs and code cannot drift (ADR-0007 D2).
# --------------------------------------------------------------------------- #

EXAMPLE_TOML: Final = """\
# .plumbline.toml — example configuration. Copy to your repo root and edit.
# Uncommented values below are the defaults; all keys are optional.
# Equivalently, use a [tool.plumbline] table in pyproject.toml.

[scan]
# Roots to scan, relative to the repo root. .gitignore is respected by default,
# and a built-in set of excludes (.venv, node_modules, build dirs, hidden dirs)
# applies unless default_excludes = false.
include = ["."]
exclude = []
respect_gitignore = true
default_excludes = true

[gate]
# The Quality Gate wired into CI. Default: fail on any Blocker, or any
# High-confidence Critical. Tighten or loosen per your risk appetite.
fail_on_severity = ["Blocker"]
fail_on_high_confidence_severity = ["Critical"]

[rules]
# Disable rules, override severity, or pass per-rule params.
disabled = []
# [rules.severity_override]
# "PLB-COST-001" = "Minor"
# [rules.params."PLB-MDL-003"]
# temperature_threshold = 0.3

[baseline]
# Accept existing findings without failing the gate (adopt incrementally).
file = ".plumbline-baseline.json"

[output]
# Any of: cli, sarif, json, html.
formats = ["cli"]
sarif_path = "plumbline.sarif"
json_path = "plumbline.json"
html_path = "plumbline.html"

[ai]
# Optional remediation enrichment. OFF by default. Detection is always
# deterministic regardless of this setting; this only tailors fix TEXT.
enrich_remediation = false
"""
