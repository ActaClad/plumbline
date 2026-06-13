"""The framework-adapter contract and registry (ADR-0004, adapter-contract.md).

Adapters translate framework APIs into the closed `SemanticTag` vocabulary so
one rule covers many frameworks. The engine gates an adapter on a file by its
trigger imports, runs all matching adapters, resolves (tag, node) conflicts by
priority, and sorts deterministically.

`FileContext` is the adapter input; in v1 it is exactly the `SourceTree`
(AST + scopes + import map), with the shared resolver in `core.values`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, runtime_checkable

from ..core.ast_layer import SourceTree
from ..model import SemanticNode, SemanticTag

#: The adapter input. Aliased so the contract can grow without touching adapters.
FileContext = SourceTree


@runtime_checkable
class Adapter(Protocol):
    """A framework adapter. Implementations are plain classes (ADR-0004 D4)."""

    name: str
    priority: int
    trigger_imports: frozenset[str]

    def annotate(self, ctx: FileContext) -> Iterable[SemanticNode]: ...


def _node_pos(n: SemanticNode) -> tuple[int, int, str]:
    line = getattr(n.node, "lineno", 0)
    col = getattr(n.node, "col_offset", 0)
    return (line, col, n.tag.value)


def collect_semantics(ctx: FileContext, adapters: Sequence[Adapter]) -> list[SemanticNode]:
    """Run every adapter whose trigger imports appear in the file, resolve
    duplicate (tag, node) annotations by adapter priority (higher wins), and
    return the result sorted by (line, column, tag) for determinism.
    """
    gated = [a for a in adapters if ctx.imported_roots & a.trigger_imports]
    # Higher priority first so it wins the (tag, node) dedupe below.
    gated.sort(key=lambda a: (-a.priority, a.name))

    chosen: dict[tuple[str, int], SemanticNode] = {}
    for adapter in gated:
        for sn in adapter.annotate(ctx):
            key = (sn.tag.value, id(sn.node))
            chosen.setdefault(key, sn)  # first (highest priority) wins
    return sorted(chosen.values(), key=_node_pos)


class SemanticIndex:
    """Rule-facing query surface over a file's semantic annotations.

    All accessors return position-sorted lists so detector iteration order is
    deterministic (ADR-0002 D3).
    """

    __slots__ = ("_by_tag", "_nodes")

    def __init__(self, nodes: Sequence[SemanticNode]) -> None:
        self._nodes = sorted(nodes, key=_node_pos)
        by_tag: dict[SemanticTag, list[SemanticNode]] = {}
        for n in self._nodes:
            by_tag.setdefault(n.tag, []).append(n)
        self._by_tag = by_tag

    def by_tag(self, tag: SemanticTag) -> list[SemanticNode]:
        return list(self._by_tag.get(tag, ()))

    def all(self) -> list[SemanticNode]:
        return list(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)
