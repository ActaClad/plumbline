"""PLB-MCP-001 — Remote MCP server with no authentication.

A FastMCP server run over a **remote** transport (`streamable-http` or `sse`)
with no `auth=`/`token_verifier=` exposes *every* registered tool — its data and
its side effects — to anyone who can reach the port. This is the "unauthenticated
MCP server" exposure class (thousands of internet-reachable MCP servers leaking
credentials and tools, 2025–26).

Detection (a sanctioned AST rule — there is no dataflow here): the file imports an
MCP SDK, constructs `FastMCP(...)` with no auth argument, AND runs a remote
transport that is not bound to loopback. It ships **Medium/advisory** because auth
can also be supplied by ASGI middleware / a reverse proxy that this file-local
view cannot see (the documented false-positive vector) — so it informs, it does
not gate.

Standards: OWASP Agentic ASI03 / MCP Top-10 MCP07 / LLM06; CWE-306.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
A remote MCP transport must authenticate callers — otherwise every tool is
reachable by anyone on the network.

Bad:
    mcp = FastMCP("my-server")
    mcp.run(transport="streamable-http")            # no auth -> tools exposed

Good:
    mcp = FastMCP("my-server", token_verifier=verifier, auth=AuthSettings(...))
    mcp.run(transport="streamable-http")
    # or bind to loopback for local-only use: mcp.run(transport="streamable-http",
    #                                                  host="127.0.0.1")
"""

_REMOTE_TRANSPORTS = frozenset({"streamable-http", "sse"})
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_REMOTE_APP_METHODS = frozenset(
    {"streamable_http_app", "sse_app", "run_streamable_http_async", "run_sse_async"}
)
_RUN_METHODS = frozenset({"run", "run_async"}) | _REMOTE_APP_METHODS
_AUTH_KWARGS = frozenset({"auth", "token_verifier", "auth_server_provider"})


def _is_fastmcp_ctor(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "FastMCP"
    return isinstance(func, ast.Attribute) and func.attr == "FastMCP"


def _has_auth(node: ast.Call) -> bool:
    return any(kw.arg in _AUTH_KWARGS for kw in node.keywords)


def _scan_transport(module: ast.Module) -> tuple[bool, bool]:
    """(remote_transport_used, bound_to_loopback) across the whole module."""
    remote = loopback = False
    for node in ast.walk(module):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        method = node.func.attr
        if method in _REMOTE_APP_METHODS:
            remote = True
        if method in _RUN_METHODS:
            for kw in node.keywords:
                if (
                    kw.arg == "transport"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value in _REMOTE_TRANSPORTS
                ):
                    remote = True
                if (
                    kw.arg == "host"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value in _LOOPBACK_HOSTS
                ):
                    loopback = True
    return remote, loopback


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    tree = ctx.tree
    if not (tree.imported_roots & {"fastmcp", "mcp"}):
        return []
    remote, loopback = _scan_transport(tree.tree)
    if not remote or loopback:
        return []  # stdio/local-only, or bound to loopback -> not network-exposed
    findings: list[FindingDraft] = []
    for node in ast.walk(tree.tree):
        if isinstance(node, ast.Call) and _is_fastmcp_ctor(node) and not _has_auth(node):
            findings.append(
                ctx.finding(
                    node,
                    "MCP server runs a remote transport (streamable-http/sse) with no "
                    "authentication (no auth=/token_verifier=); every registered tool is "
                    "reachable by anyone on the network.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-MCP-001",
    title="Remote MCP server with no authentication",
    category="MCP",
    pillar=Pillar.SECURITY,
    severity=Severity.CRITICAL,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "An unauthenticated remote MCP server exposes every tool — data and side "
        "effects — to anyone who can reach the port."
    ),
    standards=("CWE-306", "OWASP-LLM06"),
    remediation=REMEDIATION,
    detect=detect,
)
