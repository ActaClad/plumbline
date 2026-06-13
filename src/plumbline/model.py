"""The Finding data model and shared enums — the central public contract.

Every layer speaks these types. Changing this module is a public-API change and
requires a superseding ADR (CLAUDE.md §4). Pure data only: no I/O, no clock, no
network, no randomness (CLAUDE.md §1.1).

Decisions implemented here:
- ADR-0002 — Finding model, fingerprint algorithm, determinism strategy.
- ADR-0004 — `SemanticTag` vocabulary and the `Resolved` tri-state.
"""

from __future__ import annotations

import ast
import enum
import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final, final

# --------------------------------------------------------------------------- #
# Enums (ADR-0002 D1) — IntEnum with explicit ordinals so ordering and gate
# comparisons are total and deterministic.
# --------------------------------------------------------------------------- #


class Severity(enum.IntEnum):
    """Blast radius if the defect ships. Higher = worse."""

    INFO = 10
    MINOR = 20
    MAJOR = 30
    CRITICAL = 40
    BLOCKER = 50

    @property
    def label(self) -> str:
        return self.name.capitalize()


class Confidence(enum.IntEnum):
    """How sure the detector is. High may gate a build; Low is excluded from scoring."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @property
    def label(self) -> str:
        return self.name.capitalize()


class Pillar(enum.IntEnum):
    """The four pillars, in priority order (CLAUDE.md §1.7)."""

    RELIABILITY = 1
    ARCHITECTURE = 2
    HARNESS = 3
    SECURITY = 4

    @property
    def display(self) -> str:
        return _PILLAR_DISPLAY[self]


_PILLAR_DISPLAY: Final[Mapping[Pillar, str]] = {
    Pillar.RELIABILITY: "Reliability",
    Pillar.ARCHITECTURE: "Architecture & Agentic Maturity",
    Pillar.HARNESS: "Harness Engineering",
    Pillar.SECURITY: "Security",
}


# --------------------------------------------------------------------------- #
# Semantic tags (ADR-0004 D1) — closed, core-owned vocabulary. Adapters tag AST
# nodes with these; rules consume the tags, never framework call signatures.
# --------------------------------------------------------------------------- #


class SemanticTag(enum.Enum):
    LLM_CLIENT_CREATE = "LLM_CLIENT_CREATE"
    LLM_CALL = "LLM_CALL"
    AGENT_CREATE = "AGENT_CREATE"
    AGENT_INVOKE = "AGENT_INVOKE"
    AGENT_LOOP = "AGENT_LOOP"
    TOOL_DEF = "TOOL_DEF"
    TOOL_CALL = "TOOL_CALL"
    RETRIEVER_CALL = "RETRIEVER_CALL"
    EMBEDDING_CALL = "EMBEDDING_CALL"
    PROMPT_BUILD = "PROMPT_BUILD"
    MEMORY_APPEND = "MEMORY_APPEND"
    OUTPUT_PARSE = "OUTPUT_PARSE"
    TRACE_INIT = "TRACE_INIT"
    HTTP_CALL = "HTTP_CALL"


# --------------------------------------------------------------------------- #
# Resolved tri-state (ADR-0004 D2). A framework attribute (timeout, tools, …)
# is either statically Known(value), provably ABSENT, or UNKNOWN. High-confidence
# rules fire only on ABSENT — never on UNKNOWN. This is the precision mechanism.
#
# ADR-0004 names the known variant `Set(value)`; we spell it `Known` to avoid
# confusion with the builtin/typing `set`. Semantics are identical.
# --------------------------------------------------------------------------- #


class Resolved:
    """Sealed base for tri-state attribute resolution. Do not instantiate directly."""

    __slots__ = ()


@final
@dataclass(frozen=True, slots=True)
class Known(Resolved):
    """The attribute resolves statically to a constant `value`."""

    value: object


@final
class _Absent(Resolved):
    __slots__ = ()

    def __repr__(self) -> str:
        return "ABSENT"


@final
class _Unknown(Resolved):
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNKNOWN"


#: The attribute is provably not configured anywhere reachable.
ABSENT: Final[Resolved] = _Absent()
#: The attribute is configured but not statically resolvable (treat as "do not fire").
UNKNOWN: Final[Resolved] = _Unknown()


@dataclass(frozen=True, eq=False, slots=True)
class SemanticNode:
    """A normalized framework-semantics annotation on an AST node (ADR-0004 D2).

    `eq=False`: identity equality. Instances are never hashed/compared by value;
    determinism comes from sorting by source position, not from equality.
    """

    tag: SemanticTag
    node: ast.AST
    adapter: str
    attrs: Mapping[str, Resolved] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Finding (ADR-0002 D1) — frozen dataclass with EXACTLY the fields in
# architecture.md §2. `file` is a POSIX-relative string; `column` is 0-based
# internally (Python ast convention), converted to 1-based only at the SARIF
# boundary (ADR-0006 D3).
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    title: str
    category: str
    pillar: Pillar
    severity: Severity
    confidence: Confidence
    message: str
    why_it_matters: str
    file: str
    line: int
    column: int | None
    end_line: int | None
    snippet: str | None
    standards: tuple[str, ...]
    remediation: str
    fingerprint: str


@final
@dataclass(frozen=True, slots=True)
class FindingDraft:
    """A finding before its fingerprint ordinal is assigned (ADR-0002 D2).

    The finding-builder (`AnalysisContext.finding`, M1) produces drafts; the
    engine calls `assign_fingerprints` to compute the final, occurrence-aware
    fingerprints. `anchor` is the source text of the smallest enclosing
    statement — used only to compute the fingerprint, never serialized, which
    is why `Finding` itself does not carry it.
    """

    rule_id: str
    title: str
    category: str
    pillar: Pillar
    severity: Severity
    confidence: Confidence
    message: str
    why_it_matters: str
    file: str
    line: int
    column: int | None
    end_line: int | None
    snippet: str | None
    standards: tuple[str, ...]
    remediation: str
    anchor: str


@final
@dataclass(frozen=True, slots=True)
class AnalyzerError:
    """A detector/adapter/parse failure on one file. Distinct from a Finding
    (architecture.md §3). Reported, but does not abort the run (CLAUDE.md §4)."""

    file: str
    stage: str  # "parse" | "adapter:<name>" | "rule:<id>"
    message: str


# --------------------------------------------------------------------------- #
# Fingerprint (ADR-0002 D2). Line numbers are deliberately EXCLUDED so baselines
# survive unrelated edits. Occurrence ordinal `k` distinguishes identical defects
# in the same file.
# --------------------------------------------------------------------------- #

_NUL: Final = "\0"


def normalize_anchor(text: str) -> str:
    """Collapse all whitespace runs to single spaces and strip (ADR-0002 D2)."""
    return " ".join(text.split())


def compute_fingerprint(rule_id: str, file: str, anchor: str, ordinal: int) -> str:
    """sha256(rule_id ∥ file ∥ normalized-anchor ∥ ordinal)[:16] (ADR-0002 D2).

    `file` must already be a POSIX-relative path string for machine independence.
    """
    payload = _NUL.join((rule_id, file, normalize_anchor(anchor), str(ordinal)))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def assign_fingerprints(drafts: Sequence[FindingDraft]) -> list[Finding]:
    """Turn drafts into Findings with occurrence-aware fingerprints (ADR-0002 D2).

    Drafts sharing the same (rule_id, file, normalized-anchor) key are ordered by
    (line, column) and assigned ordinals 0, 1, 2, … so identical defects in one
    file get distinct, stable fingerprints. Deterministic regardless of the order
    drafts were produced in.
    """
    # Group by the fingerprint key.
    groups: dict[tuple[str, str, str], list[FindingDraft]] = {}
    for draft in drafts:
        key = (draft.rule_id, draft.file, normalize_anchor(draft.anchor))
        groups.setdefault(key, []).append(draft)

    out: list[Finding] = []
    for (rule_id, file, anchor), members in groups.items():
        ordered = sorted(members, key=lambda d: (d.line, d.column if d.column is not None else -1))
        for ordinal, d in enumerate(ordered):
            out.append(
                Finding(
                    rule_id=d.rule_id,
                    title=d.title,
                    category=d.category,
                    pillar=d.pillar,
                    severity=d.severity,
                    confidence=d.confidence,
                    message=d.message,
                    why_it_matters=d.why_it_matters,
                    file=d.file,
                    line=d.line,
                    column=d.column,
                    end_line=d.end_line,
                    snippet=d.snippet,
                    standards=d.standards,
                    remediation=d.remediation,
                    fingerprint=compute_fingerprint(rule_id, file, anchor, ordinal),
                )
            )
    return out


def finding_sort_key(f: Finding) -> tuple[str, int, int, str, str]:
    """The total, deterministic finding order (ADR-0002 D3)."""
    return (f.file, f.line, f.column if f.column is not None else -1, f.rule_id, f.fingerprint)
