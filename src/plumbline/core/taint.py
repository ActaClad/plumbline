"""The taint engine (ADR-0003, taint-engine.md).

Computes, for every expression node in a module, the set of taint labels that
reach it, with a witness path per (node, label). Forward, flow-sensitive within
a scope, path-insensitive across branches, fixpoint over statements (so
loop-carried flows like `history.append(llm_out)` are caught). Same-module
function summaries recover precision without over-tainting; any other call
returns untainted (deliberate under-taint — precision over recall, CLAUDE.md §1.4).

The engine knows nothing about sinks (ADR-0003 D4): it answers "which labels
reach this node, via which path"; rules decide what is dangerous.
"""

from __future__ import annotations

import ast
import enum
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import final

from ..adapters.base import SemanticIndex
from ..model import SemanticTag
from .ast_layer import SourceTree


class TaintLabel(enum.Enum):
    USER_INPUT = "USER_INPUT"
    LLM_OUTPUT = "LLM_OUTPUT"
    TOOL_RESULT = "TOOL_RESULT"
    RETRIEVED_CONTENT = "RETRIEVED_CONTENT"
    EXTERNAL_HTTP = "EXTERNAL_HTTP"
    PII = "PII"


@final
@dataclass(frozen=True, slots=True)
class Hop:
    line: int
    column: int
    description: str


# Semantic tag -> the label its result value carries (taint-engine §2.1).
_TAG_SOURCES: Mapping[SemanticTag, TaintLabel] = {
    SemanticTag.LLM_CALL: TaintLabel.LLM_OUTPUT,
    SemanticTag.RETRIEVER_CALL: TaintLabel.RETRIEVED_CONTENT,
    SemanticTag.TOOL_CALL: TaintLabel.TOOL_RESULT,
    SemanticTag.HTTP_CALL: TaintLabel.EXTERNAL_HTTP,
}

# Built-in framework-independent sources (taint-engine §2.2).
_INPUT_BUILTINS: frozenset[str] = frozenset({"input"})
_HTTP_MODULES: frozenset[str] = frozenset({"requests", "httpx"})
_PII_NAMES: frozenset[str] = frozenset({"email", "phone", "ssn", "aadhaar", "dob", "address"})
_PII_SUFFIXES: tuple[str, ...] = tuple(f"_{n}" for n in _PII_NAMES)

# Calls that propagate taint from arguments to result (taint-engine §3).
_PROPAGATOR_FUNCS: frozenset[str] = frozenset(
    {"str", "list", "dict", "tuple", "set", "bytes", "bytearray", "frozenset"}
)
# Sanitizers: their result cannot carry the original content (taint-engine §3).
_SANITIZERS: frozenset[str] = frozenset({"int", "float", "bool", "len", "hash", "id", "isinstance"})
# Method names that propagate taint from the receiver (str/bytes/format/join).
_PROP_METHODS: frozenset[str] = frozenset(
    {
        "strip",
        "lstrip",
        "rstrip",
        "lower",
        "upper",
        "title",
        "capitalize",
        "replace",
        "format",
        "format_map",
        "join",
        "encode",
        "decode",
        "split",
        "rsplit",
        "splitlines",
        "removeprefix",
        "removesuffix",
        "casefold",
        "expandtabs",
        "zfill",
        "center",
        "ljust",
        "rjust",
    }
)
# Dotted propagators recognized by attribute path tail.
_DOTTED_PROPAGATORS: frozenset[tuple[str, ...]] = frozenset(
    {("json", "loads"), ("json", "dumps"), ("copy", "copy"), ("copy", "deepcopy"), ("re", "sub")}
)


class TaintView:
    """Rule-facing query surface (taint-engine §5)."""

    __slots__ = ("_labels", "_witness")

    def __init__(
        self,
        labels: Mapping[int, frozenset[TaintLabel]],
        witness: Mapping[tuple[int, TaintLabel], tuple[Hop, ...]],
    ) -> None:
        self._labels = labels
        self._witness = witness

    def labels(self, node: ast.AST) -> frozenset[TaintLabel]:
        return self._labels.get(id(node), frozenset())

    def is_tainted(self, node: ast.AST, *labels: TaintLabel) -> bool:
        have = self.labels(node)
        return bool(have & set(labels)) if labels else bool(have)

    def witness(self, node: ast.AST, label: TaintLabel) -> tuple[Hop, ...]:
        return self._witness.get((id(node), label), ())


def analyze_taint(tree: SourceTree, semantics: SemanticIndex) -> TaintView:
    """Analyze a module and return a TaintView. Deterministic (ADR-0003)."""
    return _Analyzer(tree, semantics).run()


# --------------------------------------------------------------------------- #
# Implementation
# --------------------------------------------------------------------------- #

# A taint value is a label-set plus, per label, the witness path that produced it.
_Tainted = dict[TaintLabel, tuple[Hop, ...]]
_Env = dict[str, _Tainted]


def _merge(a: _Tainted, b: _Tainted) -> _Tainted:
    """Union two taint values, keeping the lexicographically-first witness per
    label for determinism (ADR-0003 D5)."""
    out: _Tainted = dict(a)
    for label, path in b.items():
        if label not in out or _path_key(path) < _path_key(out[label]):
            out[label] = path
    return out


def _path_key(path: tuple[Hop, ...]) -> tuple[tuple[int, int, str], ...]:
    return tuple((h.line, h.column, h.description) for h in path)


class _Analyzer:
    def __init__(self, tree: SourceTree, semantics: SemanticIndex) -> None:
        self._tree = tree
        # call-node id -> source label, from semantic tags.
        self._tagged: dict[int, TaintLabel] = {}
        for sn in semantics.all():
            label = _TAG_SOURCES.get(sn.tag)
            if label is not None:
                self._tagged[id(sn.node)] = label
        self._node_labels: dict[int, frozenset[TaintLabel]] = {}
        self._node_witness: dict[tuple[int, TaintLabel], tuple[Hop, ...]] = {}
        self._summaries: dict[ast.AST, frozenset[int]] = {}

    def run(self) -> TaintView:
        _SummaryComputer(self._tree, self._tagged).compute(self._summaries)
        module_env: _Env = {}
        self._exec_block(list(self._tree.tree.body), module_env)
        # Analyze each function body with module env visible (closure read).
        for node in ast.walk(self._tree.tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                self._exec_function(node, module_env)
        return TaintView(self._node_labels, self._node_witness)

    def _exec_function(self, fn: ast.FunctionDef | ast.AsyncFunctionDef, outer: _Env) -> None:
        env: _Env = dict(outer)
        line, col = getattr(fn, "lineno", 0), getattr(fn, "col_offset", 0)
        for name, label in _param_sources(fn, self._tree).items():
            hop = Hop(line, col, f"{label.value} via parameter {name!r}")
            env[name] = {label: (hop,)}
        self._exec_block(list(fn.body), env)

    # -- statements ------------------------------------------------------------

    def _exec_block(self, stmts: list[ast.stmt], env: _Env) -> None:
        for stmt in stmts:
            self._exec_stmt(stmt, env)

    def _exec_stmt(self, stmt: ast.stmt, env: _Env) -> None:
        if isinstance(stmt, ast.Assign):
            value = self._eval(stmt.value, env)
            for target in stmt.targets:
                self._bind(target, value, env)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            self._bind(stmt.target, self._eval(stmt.value, env), env)
        elif isinstance(stmt, ast.AugAssign):
            cur = env.get(_name(stmt.target), {})
            self._bind(stmt.target, _merge(cur, self._eval(stmt.value, env)), env)
        elif isinstance(stmt, ast.For):
            self._exec_for(stmt, env)
        elif isinstance(stmt, ast.While):
            self._fixpoint(stmt.body + stmt.orelse, env, cond=stmt.test)
        elif isinstance(stmt, ast.If):
            self._eval(stmt.test, env)
            self._exec_branches([stmt.body, stmt.orelse], env)
        elif isinstance(stmt, ast.With | ast.AsyncWith):
            for item in stmt.items:
                value = self._eval(item.context_expr, env)
                if item.optional_vars is not None:
                    self._bind(item.optional_vars, value, env)
            self._exec_block(list(stmt.body), env)
        elif isinstance(stmt, ast.Try):
            self._exec_branches([stmt.body, *[h.body for h in stmt.handlers], stmt.orelse], env)
            self._exec_block(list(stmt.finalbody), env)
        elif isinstance(stmt, ast.Return | ast.Expr) and stmt.value is not None:
            self._eval(stmt.value, env)
        elif isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            pass  # analyzed as their own scopes

    def _exec_for(self, stmt: ast.For, env: _Env) -> None:
        iter_value = self._eval(stmt.iter, env)
        self._bind(stmt.target, iter_value, env)  # element inherits iterable taint
        self._fixpoint(stmt.body + stmt.orelse, env, cond=None)

    def _exec_branches(self, blocks: list[list[ast.stmt]], env: _Env) -> None:
        results: list[_Env] = []
        for block in blocks:
            branch = dict(env)
            self._exec_block(list(block), branch)
            results.append(branch)
        for branch in results:
            for name, value in branch.items():
                env[name] = _merge(env.get(name, {}), value)

    def _fixpoint(self, body: list[ast.stmt], env: _Env, cond: ast.expr | None) -> None:
        # Iterate the body until the env stops growing (label sets only grow).
        for _ in range(_MAX_ITERS):
            before = _env_signature(env)
            if cond is not None:
                self._eval(cond, env)
            self._exec_block(list(body), env)
            if _env_signature(env) == before:
                return

    def _bind(self, target: ast.expr, value: _Tainted, env: _Env) -> None:
        if isinstance(target, ast.Name):
            env[target.id] = value
            self._record(target, value)
        elif isinstance(target, ast.Tuple | ast.List):
            for elt in target.elts:
                self._bind(elt, value, env)

    # -- expressions -----------------------------------------------------------

    def _eval(self, node: ast.expr, env: _Env) -> _Tainted:
        value = self._eval_inner(node, env)
        self._record(node, value)
        return value

    def _record(self, node: ast.AST, value: _Tainted) -> None:
        if not value:
            return
        existing = self._node_labels.get(id(node), frozenset())
        self._node_labels[id(node)] = existing | frozenset(value)
        for label, path in value.items():
            key = (id(node), label)
            prev = self._node_witness.get(key)
            if prev is None or _path_key(path) < _path_key(prev):
                self._node_witness[key] = path

    def _eval_inner(self, node: ast.expr, env: _Env) -> _Tainted:
        if isinstance(node, ast.Name):
            return dict(env.get(node.id, {}))
        if isinstance(node, ast.Constant):
            return {}
        if isinstance(node, ast.JoinedStr):
            return self._union([self._eval(v, env) for v in node.values])
        if isinstance(node, ast.FormattedValue):
            return self._eval(node.value, env)
        if isinstance(node, ast.BinOp):
            return _merge(self._eval(node.left, env), self._eval(node.right, env))
        if isinstance(node, ast.BoolOp):
            return self._union([self._eval(v, env) for v in node.values])
        if isinstance(node, ast.IfExp):
            return _merge(self._eval(node.body, env), self._eval(node.orelse, env))
        if isinstance(node, ast.Compare):
            for sub in [node.left, *node.comparators]:
                self._eval(sub, env)
            return {}  # comparison result is a clean bool
        if isinstance(node, ast.Await | ast.Starred):
            return self._eval(node.value, env)
        if isinstance(node, ast.Attribute):
            return self._eval(node.value, env)  # x.text inherits x's taint
        if isinstance(node, ast.Subscript):
            self._eval(node.slice, env)
            return self._eval(node.value, env)  # element inherits container taint
        if isinstance(node, ast.List | ast.Tuple | ast.Set):
            return self._union([self._eval(e, env) for e in node.elts])
        if isinstance(node, ast.Dict):
            parts = [self._eval(v, env) for v in node.values if v is not None]
            return self._union(parts)
        if isinstance(node, ast.NamedExpr):
            value = self._eval(node.value, env)
            self._bind(node.target, value, env)
            return value
        if isinstance(node, ast.Call):
            return self._eval_call(node, env)
        return {}

    def _eval_call(self, node: ast.Call, env: _Env) -> _Tainted:
        # 1. Source call (semantic tag or built-in) — result IS the source.
        src = self._call_source(node)
        if src is not None:
            label, desc = src
            hop = Hop(getattr(node, "lineno", 0), getattr(node, "col_offset", 0), desc)
            for arg in [*node.args, *(k.value for k in node.keywords)]:
                self._eval(arg, env)  # still record arg taint
            return {label: (hop,)}

        func = node.func
        name = func.id if isinstance(func, ast.Name) else None
        arg_values = [self._eval(a, env) for a in node.args]
        kw_values = [self._eval(k.value, env) for k in node.keywords]

        if name in _SANITIZERS:
            return {}
        if name in _PROPAGATOR_FUNCS:
            return self._union(arg_values + kw_values)
        if isinstance(func, ast.Attribute):
            recv = self._eval(func.value, env)
            if func.attr in _PROP_METHODS:
                return self._union([recv, *arg_values, *kw_values])
            if _dotted(func) in _DOTTED_PROPAGATORS:
                return self._union(arg_values + kw_values)
            return {}  # unknown method -> under-taint
        if name is not None:
            summary = self._summary_for(name)
            if summary is not None:
                return self._union([arg_values[i] for i in summary if i < len(arg_values)])
        return {}  # unknown call -> untainted (ADR-0003 D3)

    def _call_source(self, node: ast.Call) -> tuple[TaintLabel, str] | None:
        line = getattr(node, "lineno", 0)
        tagged = self._tagged.get(id(node))
        if tagged is not None:
            return tagged, f"{tagged.value} from {_describe(node)} (line {line})"
        func = node.func
        if isinstance(func, ast.Name) and func.id in _INPUT_BUILTINS:
            return TaintLabel.USER_INPUT, f"user input via input() (line {line})"
        if isinstance(func, ast.Attribute):
            root = _root_name(func)
            if root in _HTTP_MODULES:
                return TaintLabel.EXTERNAL_HTTP, f"external HTTP via {root} (line {line})"
        return None

    def _summary_for(self, name: str) -> frozenset[int] | None:
        for fn, summary in self._summaries.items():
            if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef) and fn.name == name:
                return summary
        return None

    @staticmethod
    def _union(values: list[_Tainted]) -> _Tainted:
        out: _Tainted = {}
        for v in values:
            out = _merge(out, v)
        return out


_MAX_ITERS = 1000  # fixpoint guard; label sets are finite so this is never hit in practice


def _iunion(parts: Iterable[frozenset[int]]) -> frozenset[int]:
    """Union an iterable of int-label sets (summary domain)."""
    out: set[int] = set()
    for p in parts:
        out |= p
    return frozenset(out)


def _env_signature(env: _Env) -> frozenset[tuple[str, TaintLabel]]:
    return frozenset((name, label) for name, value in env.items() for label in value)


def _param_sources(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, tree: SourceTree
) -> dict[str, TaintLabel]:
    """Built-in parameter sources: web-handler params -> USER_INPUT; PII-named
    params -> PII (heuristic; taint-engine §2.2)."""
    out: dict[str, TaintLabel] = {}
    is_handler = _is_web_handler(fn)
    for arg in [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]:
        if _is_pii_name(arg.arg):
            out[arg.arg] = TaintLabel.PII
        elif is_handler:
            out[arg.arg] = TaintLabel.USER_INPUT
    return out


_HANDLER_DECORATORS: frozenset[str] = frozenset({"route", "get", "post", "put", "delete", "patch"})


def _is_web_handler(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in fn.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Attribute) and target.attr in _HANDLER_DECORATORS:
            return True
    return False


def _is_pii_name(name: str) -> bool:
    return name in _PII_NAMES or name.endswith(_PII_SUFFIXES)


def _name(node: ast.expr) -> str:
    return node.id if isinstance(node, ast.Name) else ""


def _attr_tail(func: ast.Attribute) -> list[str]:
    names: list[str] = []
    cur: ast.expr = func
    while isinstance(cur, ast.Attribute):
        names.append(cur.attr)
        cur = cur.value
    names.reverse()
    return names


def _root_name(node: ast.expr) -> str | None:
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        cur = cur.value
    return cur.id if isinstance(cur, ast.Name) else None


def _dotted(func: ast.Attribute) -> tuple[str, ...]:
    """Full dotted path including the root name: `json.loads` -> ('json', 'loads')."""
    root = _root_name(func)
    return (root, *_attr_tail(func)) if root is not None else tuple(_attr_tail(func))


def _describe(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return f"{'.'.join(_attr_tail(func))}()"
    if isinstance(func, ast.Name):
        return f"{func.id}()"
    return "call"


# --------------------------------------------------------------------------- #
# Function summaries (taint-engine §4): which param indices' taint reaches return.
# --------------------------------------------------------------------------- #


class _SummaryComputer:
    """Bottom-up, fixpoint over the module call graph (recursion starts empty)."""

    def __init__(self, tree: SourceTree, tagged: dict[int, TaintLabel]) -> None:
        self._tree = tree
        self._tagged = tagged
        self._functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        for node in ast.walk(tree.tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                self._functions[node.name] = node

    def compute(self, out: dict[ast.AST, frozenset[int]]) -> None:
        current: dict[str, frozenset[int]] = {n: frozenset() for n in self._functions}
        for _ in range(_MAX_ITERS):
            changed = False
            for fname, fn in self._functions.items():
                summary = self._summarize(fn, current)
                if summary != current[fname]:
                    current[fname] = summary
                    changed = True
            if not changed:
                break
        for fname, fn in self._functions.items():
            out[fn] = current[fname]

    def _summarize(
        self, fn: ast.FunctionDef | ast.AsyncFunctionDef, known: dict[str, frozenset[int]]
    ) -> frozenset[int]:
        params = [a.arg for a in [*fn.args.posonlyargs, *fn.args.args]]
        # Param-index taint domain: each param seeded with its own index.
        env: dict[str, frozenset[int]] = {name: frozenset({i}) for i, name in enumerate(params)}
        reached: set[int] = set()
        self._walk(list(fn.body), env, reached, known)
        return frozenset(reached)

    def _walk(
        self,
        stmts: list[ast.stmt],
        env: dict[str, frozenset[int]],
        reached: set[int],
        known: dict[str, frozenset[int]],
    ) -> None:
        for _ in range(_MAX_ITERS):
            before = dict(env)
            before_reached = set(reached)
            for stmt in stmts:
                self._walk_stmt(stmt, env, reached, known)
            if env == before and reached == before_reached:
                return

    def _walk_stmt(
        self,
        stmt: ast.stmt,
        env: dict[str, frozenset[int]],
        reached: set[int],
        known: dict[str, frozenset[int]],
    ) -> None:
        if isinstance(stmt, ast.Assign):
            value = self._expr(stmt.value, env, known)
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    env[target.id] = value
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            if isinstance(stmt.target, ast.Name):
                env[stmt.target.id] = self._expr(stmt.value, env, known)
        elif isinstance(stmt, ast.Return) and stmt.value is not None:
            reached |= self._expr(stmt.value, env, known)
        elif isinstance(stmt, ast.If):
            self._walk(stmt.body, env, reached, known)
            self._walk(stmt.orelse, env, reached, known)
        elif isinstance(stmt, ast.For):
            env[_name(stmt.target)] = self._expr(stmt.iter, env, known)
            self._walk(stmt.body, env, reached, known)
        elif isinstance(stmt, ast.While):
            self._walk(stmt.body, env, reached, known)
        elif isinstance(stmt, ast.With | ast.AsyncWith):
            self._walk(list(stmt.body), env, reached, known)

    def _expr(
        self, node: ast.expr, env: dict[str, frozenset[int]], known: dict[str, frozenset[int]]
    ) -> frozenset[int]:
        def ev(n: ast.expr) -> frozenset[int]:
            return self._expr(n, env, known)

        if isinstance(node, ast.Name):
            return env.get(node.id, frozenset())
        if isinstance(node, ast.JoinedStr):
            return _iunion(ev(v) for v in node.values)
        if isinstance(node, ast.FormattedValue | ast.Attribute | ast.Starred | ast.Await):
            return ev(node.value)
        if isinstance(node, ast.Subscript):
            return ev(node.value)
        if isinstance(node, ast.BinOp):
            return ev(node.left) | ev(node.right)
        if isinstance(node, ast.BoolOp):
            return _iunion(ev(v) for v in node.values)
        if isinstance(node, ast.IfExp):
            return ev(node.body) | ev(node.orelse)
        if isinstance(node, ast.List | ast.Tuple | ast.Set):
            return _iunion(ev(e) for e in node.elts)
        if isinstance(node, ast.Call):
            return self._call(node, env, known)
        return frozenset()

    def _call(
        self, node: ast.Call, env: dict[str, frozenset[int]], known: dict[str, frozenset[int]]
    ) -> frozenset[int]:
        if id(node) in self._tagged:
            return frozenset()  # source result doesn't carry param taint
        func = node.func
        name = func.id if isinstance(func, ast.Name) else None
        args = [self._expr(a, env, known) for a in node.args]
        if name in _SANITIZERS:
            return frozenset()
        if name in _PROPAGATOR_FUNCS:
            return _iunion(args)
        if isinstance(func, ast.Attribute):
            recv = self._expr(func.value, env, known)
            if func.attr in _PROP_METHODS:
                return _iunion([recv, *args])
            if _dotted(func) in _DOTTED_PROPAGATORS:
                return _iunion(args)
            return frozenset()
        if name is not None and name in known:
            return _iunion(args[i] for i in known[name] if i < len(args))
        return frozenset()
