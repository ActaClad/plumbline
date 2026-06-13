"""The rule-plugin contract, analysis contexts, and convention discovery.

Decisions: ADR-0005 (discovery + validation), ADR-0010 (file vs project scope),
rule-plugin-contract.md (the authoring contract). A rule is one module exposing
a module-level `RULE = Rule(...)`. Adding a rule never edits a central registry.

The finding-builder (`AnalysisContext.finding`) is the ONLY sanctioned way to
create findings — it produces `FindingDraft`s carrying the fingerprint anchor;
the engine finalizes them with occurrence-aware fingerprints (ADR-0002 D2).
"""

from __future__ import annotations

import ast
import enum
import importlib
import pkgutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final, final

from ..adapters.base import SemanticIndex
from ..config import Config
from ..core.ast_layer import SourceTree
from ..model import (
    Confidence,
    FindingDraft,
    Pillar,
    Severity,
)

KNOWN_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"RES", "AGT", "MDL", "OUT", "TOOL", "RAG", "PRM", "EVAL", "OBS", "COST", "SEC", "GOV"}
)


class RuleLoadError(Exception):
    """A malformed or duplicate rule. Aborts the run with exit code 3 (ADR-0005 D2):
    a broken rule set must never half-run."""


class RuleScope(enum.Enum):
    """ADR-0010 D1. FILE rules run once per file; PROJECT rules run once per run
    over a ProjectContext."""

    FILE = "file"
    PROJECT = "project"


# --------------------------------------------------------------------------- #
# Analysis state
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class FileAnalysis:
    """The per-file analysis products, computed once and shared by every rule.
    (`taint` is added in M1 when the taint engine lands — implementation-plan M1.)
    """

    file: str  # POSIX-relative
    tree: SourceTree
    semantics: SemanticIndex


class AnalysisContext:
    """Per-(file, rule) view passed to a FILE rule's `detect`. Read-only access
    to the shared file analysis plus a finding-builder bound to the rule."""

    __slots__ = ("_analysis", "config", "rule")

    def __init__(self, analysis: FileAnalysis, rule: Rule, config: Config) -> None:
        self._analysis = analysis
        self.rule = rule
        self.config = config

    @property
    def file(self) -> str:
        return self._analysis.file

    @property
    def tree(self) -> SourceTree:
        return self._analysis.tree

    @property
    def semantics(self) -> SemanticIndex:
        return self._analysis.semantics

    def finding(
        self,
        node: ast.AST,
        message: str,
        *,
        severity: Severity | None = None,
        confidence: Confidence | None = None,
        end_line: int | None = None,
    ) -> FindingDraft:
        return _build_draft(
            self.rule, self.config, self._analysis.tree, self.file, node, message,
            severity=severity, confidence=confidence, end_line=end_line,
        )


class ProjectContext:
    """Passed to a PROJECT rule's `detect`, once per run after all files are
    analyzed (ADR-0010 D1). Findings still anchor to a real (file, node)."""

    __slots__ = ("_by_file", "config", "files", "rule")

    def __init__(self, files: Sequence[FileAnalysis], rule: Rule, config: Config) -> None:
        self.files = tuple(files)
        self._by_file = {f.file: f for f in files}
        self.rule = rule
        self.config = config

    def finding(
        self,
        file: str,
        node: ast.AST,
        message: str,
        *,
        severity: Severity | None = None,
        confidence: Confidence | None = None,
        end_line: int | None = None,
    ) -> FindingDraft:
        tree = self._by_file[file].tree
        return _build_draft(
            self.rule, self.config, tree, file, node, message,
            severity=severity, confidence=confidence, end_line=end_line,
        )


def _build_draft(
    rule: Rule,
    config: Config,
    tree: SourceTree,
    file: str,
    node: ast.AST,
    message: str,
    *,
    severity: Severity | None,
    confidence: Confidence | None,
    end_line: int | None,
) -> FindingDraft:
    # Effective severity: per-rule config override unless the call overrides it
    # explicitly (ADR-0002 D1, ADR-0007).
    eff_sev = severity or config.rules.severity_override.get(rule.id, rule.severity)
    eff_conf = confidence or rule.confidence
    line = getattr(node, "lineno", 1)
    column = getattr(node, "col_offset", None)
    end = end_line if end_line is not None else getattr(node, "end_lineno", None)
    return FindingDraft(
        rule_id=rule.id,
        title=rule.title,
        category=rule.category,
        pillar=rule.pillar,
        severity=eff_sev,
        confidence=eff_conf,
        message=message,
        why_it_matters=rule.why_it_matters,
        file=file,
        line=line,
        column=column,
        end_line=end,
        snippet=tree.segment(node),
        standards=rule.standards,
        remediation=rule.remediation,
        anchor=tree.anchor_text(node),
    )


# --------------------------------------------------------------------------- #
# The Rule object
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    title: str
    category: str
    pillar: Pillar
    severity: Severity
    confidence: Confidence
    why_it_matters: str
    remediation: str
    detect: Callable[..., list[FindingDraft]]
    standards: tuple[str, ...] = ()
    scope: RuleScope = RuleScope.FILE


# --------------------------------------------------------------------------- #
# Discovery + validation (ADR-0005)
# --------------------------------------------------------------------------- #


def _expected_module_basename(rule_id: str) -> str:
    return rule_id.lower().replace("-", "_")


def _validate(rule: Rule, module_name: str) -> None:
    parts = rule.id.split("-")
    if len(parts) != 3 or parts[0] != "PLB" or not parts[2].isdigit():
        raise RuleLoadError(f"{module_name}: malformed rule id {rule.id!r} (want PLB-<CAT>-<NNN>)")
    category = parts[1]
    if category not in KNOWN_CATEGORIES:
        raise RuleLoadError(f"{rule.id}: unknown category {category!r}")
    if rule.category != category:
        raise RuleLoadError(
            f"{rule.id}: category field {rule.category!r} != id category {category!r}"
        )
    basename = module_name.rsplit(".", 1)[-1]
    expected = _expected_module_basename(rule.id)
    if basename != expected:
        raise RuleLoadError(
            f"{rule.id}: must live in a module named {expected!r}, found {basename!r} (ADR-0005 D2)"
        )
    if not rule.title.strip() or not rule.why_it_matters.strip() or not rule.remediation.strip():
        raise RuleLoadError(f"{rule.id}: title, why_it_matters, and remediation must be non-empty")


def discover_rules() -> list[Rule]:
    """Import every module under `plumbline.rules`, collect `RULE` objects, and
    validate them. Sorted by ID. Raises RuleLoadError on any problem."""
    import plumbline.rules as pkg

    found: dict[str, Rule] = {}
    module_of: dict[str, str] = {}
    infos = sorted(
        pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."), key=lambda m: m.name
    )
    for info in infos:
        try:
            module = importlib.import_module(info.name)
        except Exception as exc:  # noqa: BLE001 — a bad rule module must fail loud
            raise RuleLoadError(f"{info.name}: failed to import ({exc})") from exc
        rule = getattr(module, "RULE", None)
        if not isinstance(rule, Rule):
            continue
        _validate(rule, info.name)
        if rule.id in found:
            raise RuleLoadError(
                f"duplicate rule id {rule.id!r} in {info.name} and {module_of[rule.id]}"
            )
        found[rule.id] = rule
        module_of[rule.id] = info.name
    return [found[rule_id] for rule_id in sorted(found)]
