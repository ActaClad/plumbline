"""Shared helpers for the project-scope harness rules (EVAL-001, OBS-001).

These are *absence* rules: they fire when LLM/agent code exists but a harness
signal (an eval suite, tracing) is absent anywhere in the scanned tree. The
helpers here answer the two questions both rules share — "is there agentic code,
and where is its first call (the anchor)?" — and provide the import/path
primitives their evidence checks build on. See `docs/specs/harness-rules.md`.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Sequence

from ..model import SemanticTag
from .base import FileAnalysis

# Tags that mean "this project contains LLM/agent code at all".
_AGENTIC_TAGS: tuple[SemanticTag, ...] = (
    SemanticTag.LLM_CALL,
    SemanticTag.AGENT_CREATE,
    SemanticTag.AGENT_INVOKE,
)

# Shared scan-scope caveat appended to every harness finding (spec §1).
SCOPE_CAVEAT = (
    " Note: harness rules reason about the whole repo — scan the project root "
    "(including tests/ and CI), not just src/."
)


def agentic_anchor(files: Sequence[FileAnalysis]) -> tuple[str, ast.AST] | None:
    """The (file, node) of the first model call in sorted file order, or the
    first agent construct if there is no raw LLM_CALL. None ⇒ no agentic code
    (the rule is N/A and must stay silent). Anchors findings per ADR-0010 D2."""
    ordered = sorted(files, key=lambda f: f.file)
    for tag in _AGENTIC_TAGS:
        for fa in ordered:
            nodes = fa.semantics.by_tag(tag)
            if nodes:
                return fa.file, nodes[0].node
    return None


def imported_modules(fa: FileAnalysis) -> set[str]:
    """Every dotted module path imported by a file (`from a.b import c` ⇒ 'a.b';
    `import a.b` ⇒ 'a.b')."""
    return {info.module for info in fa.tree.imports.values()}


def agentic_module_names(files: Iterable[FileAnalysis]) -> set[str]:
    """Module names (full dotted path + bare stem) of every file that carries
    LLM/agent semantics — the targets a test file must import to count as
    'exercises the LLM paths'."""
    out: set[str] = set()
    for fa in files:
        if any(fa.semantics.by_tag(t) for t in _AGENTIC_TAGS):
            out |= _module_names(fa.file)
    return out


def is_test_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
        or path.startswith("tests/")
        or "/tests/" in f"/{path}"
    )


def string_constants(fa: FileAnalysis) -> set[str]:
    """All string-literal constants in a file (used to spot in-code references to
    env-var-configured tracing, e.g. 'LANGCHAIN_TRACING_V2')."""
    return {
        n.value
        for n in ast.walk(fa.tree.tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def _module_names(path: str) -> set[str]:
    stem = path[:-3] if path.endswith(".py") else path
    parts = stem.split("/")
    return {".".join(parts), parts[-1]}
