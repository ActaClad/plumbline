"""The AST layer: a thin wrapper over stdlib `ast` (ADR-0009).

Detection parses with stdlib `ast` — fast, zero-dependency, and sufficient
(detection needs structure, positions, and source snippets, not the lossless
formatting fidelity libcst exists for). This module is the rule-facing surface;
rules and adapters read it, never raw `ast` plumbing.

Provides: parse with syntax-error containment, a parent map, the smallest
enclosing statement (for fingerprint anchors), source segments, a scope tree
with simple name bindings, an import map (for adapter gating and name
resolution), and the inline-suppression scan (ADR-0006 D6, read via tokenize
because the AST drops comments).
"""

from __future__ import annotations

import ast
import enum
import io
import re
import tokenize
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import final


class ParseError(Exception):
    """The file is not valid Python for the running interpreter (ADR-0009 risk a).

    The engine converts this to an AnalyzerError for the file and continues.
    """


# --------------------------------------------------------------------------- #
# Scopes
# --------------------------------------------------------------------------- #


class ScopeKind(enum.Enum):
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    LAMBDA = "lambda"


@final
@dataclass(eq=False, slots=True)
class Scope:
    """A lexical scope. `assigns` maps a locally-bound name to the RHS value
    expressions assigned to it (for constant folding in core/values.py);
    `params` are parameter names; `node` is the scope-defining AST node."""

    kind: ScopeKind
    node: ast.AST
    parent: Scope | None
    assigns: dict[str, list[ast.expr]] = field(default_factory=dict)
    params: set[str] = field(default_factory=set)


@final
@dataclass(frozen=True, slots=True)
class ImportedName:
    """How a local name maps to a dotted origin.

    `import openai`            -> ImportedName("openai", "", "openai")
    `import openai as oa`      -> ImportedName("openai", "", "oa")
    `from openai import OpenAI`-> ImportedName("openai", "OpenAI", "OpenAI")
    `from openai import OpenAI as C` -> ImportedName("openai", "OpenAI", "C")
    """

    module: str
    qualname: str
    asname: str


# --------------------------------------------------------------------------- #
# SourceTree
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class Suppressions:
    """Inline `# plumb: ignore[...]` directives (ADR-0006 D6)."""

    by_line: Mapping[int, frozenset[str]]
    invalid_lines: tuple[int, ...]  # bare `# plumb: ignore` with no rule id


@final
@dataclass(frozen=True, slots=True)
class SourceTree:
    file: str  # POSIX-relative path string
    source: str
    tree: ast.Module
    module_scope: Scope
    imports: Mapping[str, ImportedName]
    imported_roots: frozenset[str]  # top-level module roots imported anywhere
    suppressions: Suppressions
    _parents: Mapping[int, ast.AST]
    _scopes: Mapping[int, Scope]

    def parent(self, node: ast.AST) -> ast.AST | None:
        return self._parents.get(id(node))

    def scope_of(self, node: ast.AST) -> Scope:
        """The lexical scope a node belongs to (defaults to module scope)."""
        return self._scopes.get(id(node), self.module_scope)

    def enclosing_statement(self, node: ast.AST) -> ast.stmt:
        """Smallest statement containing `node` — the fingerprint anchor (ADR-0002 D2)."""
        cur: ast.AST | None = node
        while cur is not None:
            if isinstance(cur, ast.stmt):
                return cur
            cur = self.parent(cur)
        # A module has no enclosing statement; fall back to the node coerced to one
        # is impossible — every expression in a module lives under a statement.
        raise ValueError("node has no enclosing statement")  # pragma: no cover

    def segment(self, node: ast.AST) -> str | None:
        """Exact source text of a node, or None if positions are unavailable."""
        return ast.get_source_segment(self.source, node)

    def anchor_text(self, node: ast.AST) -> str:
        """Source of the enclosing statement; used to compute fingerprints."""
        seg = self.segment(self.enclosing_statement(node))
        return seg if seg is not None else ""


# --------------------------------------------------------------------------- #
# Building
# --------------------------------------------------------------------------- #


def parse(file: str, source: str) -> SourceTree:
    """Parse `source` into a SourceTree. Raises ParseError on a syntax error."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ParseError(f"{file}: {exc.msg} (line {exc.lineno})") from exc

    parents: dict[int, ast.AST] = {}
    scopes: dict[int, Scope] = {}
    module_scope = Scope(kind=ScopeKind.MODULE, node=tree, parent=None)
    imports: dict[str, ImportedName] = {}
    imported_roots: set[str] = set()

    _Builder(parents, scopes, imports, imported_roots).build(tree, module_scope)

    return SourceTree(
        file=file,
        source=source,
        tree=tree,
        module_scope=module_scope,
        imports=imports,
        imported_roots=frozenset(imported_roots),
        suppressions=scan_suppressions(source),
        _parents=parents,
        _scopes=scopes,
    )


_SCOPE_KIND: Mapping[type[ast.AST], ScopeKind] = {
    ast.FunctionDef: ScopeKind.FUNCTION,
    ast.AsyncFunctionDef: ScopeKind.FUNCTION,
    ast.Lambda: ScopeKind.LAMBDA,
    ast.ClassDef: ScopeKind.CLASS,
}


class _Builder:
    """Single-pass builder: parent map, scope tree, bindings, imports."""

    def __init__(
        self,
        parents: dict[int, ast.AST],
        scopes: dict[int, Scope],
        imports: dict[str, ImportedName],
        imported_roots: set[str],
    ) -> None:
        self._parents = parents
        self._scopes = scopes
        self._imports = imports
        self._imported_roots = imported_roots

    def build(self, node: ast.AST, scope: Scope) -> None:
        self._scopes[id(node)] = scope
        self._record_bindings(node, scope)

        child_scope = self._child_scope_for(node, scope)
        for child in ast.iter_child_nodes(node):
            self._parents[id(child)] = node
            self.build(child, child_scope if child_scope is not None else scope)

    def _child_scope_for(self, node: ast.AST, scope: Scope) -> Scope | None:
        kind = _SCOPE_KIND.get(type(node))
        if kind is None:
            return None
        new_scope = Scope(kind=kind, node=node, parent=scope)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            for arg in _all_args(node.args):
                new_scope.params.add(arg.arg)
        return new_scope

    def _record_bindings(self, node: ast.AST, scope: Scope) -> None:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                self._bind_target(target, node.value, scope)
        elif isinstance(node, ast.AnnAssign | ast.NamedExpr):
            # AnnAssign.value is optional (`x: int`); NamedExpr.value is not.
            if node.value is not None:
                self._bind_target(node.target, node.value, scope)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                self._imported_roots.add(root)
                self._imports[alias.asname or alias.name] = ImportedName(
                    module=alias.name, qualname="", asname=alias.asname or alias.name
                )
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            root = node.module.split(".")[0]
            self._imported_roots.add(root)
            for alias in node.names:
                local = alias.asname or alias.name
                self._imports[local] = ImportedName(
                    module=node.module, qualname=alias.name, asname=local
                )

    def _bind_target(self, target: ast.expr, value: ast.expr, scope: Scope) -> None:
        if isinstance(target, ast.Name):
            scope.assigns.setdefault(target.id, []).append(value)


def _all_args(args: ast.arguments) -> list[ast.arg]:
    result = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
    if args.vararg is not None:
        result.append(args.vararg)
    if args.kwarg is not None:
        result.append(args.kwarg)
    return result


# --------------------------------------------------------------------------- #
# Inline suppressions (ADR-0006 D6)
# --------------------------------------------------------------------------- #

# Anchored at the comment start (matched with .match, not .search): a suppression
# directive must BE the comment — `# plumb: ignore[ID]` — not appear inside prose
# that merely mentions the syntax (e.g. a doc comment "bare `# plumb: ignore`").
_IGNORE_RE = re.compile(r"#\s*plumb:\s*ignore(?:\[(?P<ids>[^\]]*)\])?", re.IGNORECASE)


def scan_suppressions(source: str) -> Suppressions:
    """Parse `# plumb: ignore[PLB-...]` comments. A bare `ignore` with no rule
    id is invalid (blanket suppression hides defects) and recorded separately."""
    by_line: dict[int, frozenset[str]] = {}
    invalid: list[int] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        comments = [(t.start[0], t.string) for t in tokens if t.type == tokenize.COMMENT]
    except (tokenize.TokenError, IndentationError):
        # Suppression scanning is best-effort; a tokenizer hiccup must not abort.
        return Suppressions(by_line={}, invalid_lines=())

    for lineno, text in comments:
        match = _IGNORE_RE.match(text)  # anchored — the directive must start the comment
        if match is None:
            continue
        ids_raw = match.group("ids")
        if ids_raw is None or not ids_raw.strip():
            invalid.append(lineno)
            continue
        ids = frozenset(part.strip() for part in ids_raw.split(",") if part.strip())
        if ids:
            by_line[lineno] = ids
        else:
            invalid.append(lineno)
    return Suppressions(by_line=by_line, invalid_lines=tuple(sorted(invalid)))
