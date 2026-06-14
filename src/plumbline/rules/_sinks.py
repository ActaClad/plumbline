"""Dangerous-sink detectors shared by the SEC rules.

The taint engine knows nothing about sinks (ADR-0003 D4) — rules decide what is
dangerous. This module is that catalog: given a `Call`, each detector returns the
argument node that must be taint-checked, or None if the call is not that sink.

Each detector is written to its sink's **safe form** so it does not fire on
benign code (the precision discipline, CLAUDE.md §1.4): e.g. the SQL detector
returns the *query-string* arg only (a parameterized query has a constant query
and is silent), and the shell detector fires on `subprocess(..., shell=True)` but
not the list-argv form.
"""

from __future__ import annotations

import ast

from ..core.ast_layer import SourceTree
from ..core.values import resolve_call_keyword
from ..model import Known

# --------------------------------------------------------------------------- #
# Code execution: eval / exec / compile (SEC-002)
# --------------------------------------------------------------------------- #

_CODE_EXEC: frozenset[str] = frozenset({"eval", "exec", "compile"})


def code_exec_sink(call: ast.Call) -> ast.expr | None:
    """`eval(x)` / `exec(x)` / `compile(x, …)` builtins -> the code arg."""
    func = call.func
    if isinstance(func, ast.Name) and func.id in _CODE_EXEC and call.args:
        return call.args[0]
    return None


# --------------------------------------------------------------------------- #
# Shell execution: os.system/popen, subprocess.* with shell=True (SEC-003)
# --------------------------------------------------------------------------- #

_OS_SHELL: frozenset[str] = frozenset({"system", "popen"})
_SUBPROCESS_FNS: frozenset[str] = frozenset({"run", "call", "check_call", "check_output", "Popen"})


def shell_sink(tree: SourceTree, call: ast.Call) -> ast.expr | None:
    """A shell-interpreted command arg: `os.system(x)`/`os.popen(x)`, or a
    `subprocess.*` call with `shell=True`. The argv-list form (`shell` absent or
    False) is safe — no shell to inject — and returns None."""
    func = call.func
    if not isinstance(func, ast.Attribute) or not call.args:
        return None
    root = _root(func)
    if func.attr in _OS_SHELL and root == "os":
        return call.args[0]
    if func.attr in _SUBPROCESS_FNS and root == "subprocess":
        shell = resolve_call_keyword(tree, tree.scope_of(call), call, "shell")
        if isinstance(shell, Known) and shell.value is True:
            return call.args[0]
    return None


# --------------------------------------------------------------------------- #
# SQL: cursor.execute(query, …) — fire only on a tainted QUERY STRING (SEC-005)
# --------------------------------------------------------------------------- #

_SQL_FNS: frozenset[str] = frozenset({"execute", "executemany", "executescript"})


def sql_query_sink(call: ast.Call) -> ast.expr | None:
    """`<cursor|conn|engine>.execute(query, params)` -> the query arg (arg 0).
    Returning arg 0 ONLY is the precision crux: a parameterized query has a
    constant query string (untainted) and bound params in arg 1, so it stays
    silent; only a query built by f-string/concat is tainted and fires."""
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr in _SQL_FNS and call.args:
        return call.args[0]
    return None


# --------------------------------------------------------------------------- #
# HTML rendering: only the explicitly-unsafe sinks (SEC-006)
# --------------------------------------------------------------------------- #

# Jinja2 `render_template` autoescapes by default and is NOT a sink — only the
# unescaped paths are.
_HTML_UNSAFE_FNS: frozenset[str] = frozenset({"render_template_string", "Markup"})


def html_sink(call: ast.Call) -> ast.expr | None:
    """`render_template_string(x)` / `Markup(x)` / `markupsafe.Markup(x)` -> the
    content arg. Excludes autoescaped `render_template(...)`."""
    func = call.func
    name = (
        func.attr
        if isinstance(func, ast.Attribute)
        else (func.id if isinstance(func, ast.Name) else None)
    )
    if name in _HTML_UNSAFE_FNS and call.args:
        return call.args[0]
    return None


# --------------------------------------------------------------------------- #
# Outbound HTTP: requests/httpx/urllib — the URL arg (SEC-007)
# --------------------------------------------------------------------------- #

_HTTP_VERBS: frozenset[str] = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "request"}
)
_HTTP_ROOTS: frozenset[str] = frozenset({"requests", "httpx", "aiohttp", "urllib3"})


def http_url_sink(call: ast.Call) -> ast.expr | None:
    """An outbound HTTP call -> the URL arg (arg 0): `requests.get(url)`,
    `httpx.post(url, …)`, `urllib.request.urlopen(url)`."""
    func = call.func
    if not isinstance(func, ast.Attribute) or not call.args:
        return None
    root = _root(func)
    if func.attr in _HTTP_VERBS and root in _HTTP_ROOTS:
        return call.args[0]
    if func.attr == "urlopen":  # urllib.request.urlopen
        return call.args[0]
    return None


# --------------------------------------------------------------------------- #
# Logging: logger.*/logging.*/print — the logged args (GOV-002)
# --------------------------------------------------------------------------- #

_LOG_LEVELS: frozenset[str] = frozenset({"debug", "info", "warning", "warn", "error", "exception"})


def log_args(call: ast.Call) -> list[ast.expr]:
    """A logging call -> its message args (to taint-check for prompt/response
    content). `logger.info(x)`, `logging.debug(x)`, `print(x)`."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "print":
        return list(call.args)
    if isinstance(func, ast.Attribute) and func.attr in _LOG_LEVELS:
        return list(call.args)
    return []


def _root(func: ast.expr) -> str | None:
    cur: ast.expr = func
    while isinstance(cur, ast.Attribute):
        cur = cur.value
    return cur.id if isinstance(cur, ast.Name) else None
