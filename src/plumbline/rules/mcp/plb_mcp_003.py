"""PLB-MCP-003 — Over-broad / wildcard MCP OAuth scopes.

The MCP spec's own scope-minimization guidance warns against omnibus scopes:
a wildcard (`*`, `admin:*`, `files:*`, `full-access`) turns a single stolen or
over-shared token into total blast radius. This detects such scopes declared in
an MCP server's auth configuration.

A pattern rule over literal scope lists (no dataflow applies to a static config
list). It matches `required_scopes=/scopes_supported=/scopes=` list literals whose
string elements are wildcard/omnibus. Ships **Medium/advisory**.

Standards: OWASP Agentic ASI03 / MCP Top-10 MCP02 / LLM06; CWE-250.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Request the minimal scopes a caller needs — never a wildcard.

Bad:
    AuthSettings(required_scopes=["*"])            # or ["admin:*"], ["full-access"]

Good:
    AuthSettings(required_scopes=["weather:read"]) # least privilege
"""

_SCOPE_KWARGS = frozenset({"required_scopes", "scopes_supported", "scopes"})
_OMNIBUS = frozenset({"*", "all", "full-access", "fullaccess", "admin", "root", "superuser"})


def _is_broad(scope: str) -> bool:
    s = scope.strip().lower()
    return s in _OMNIBUS or s.endswith(":*") or "*" in s


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    tree = ctx.tree
    if not (tree.imported_roots & {"fastmcp", "mcp"}):
        return []
    findings: list[FindingDraft] = []
    for node in ast.walk(tree.tree):
        if not (
            isinstance(node, ast.keyword)
            and node.arg in _SCOPE_KWARGS
            and isinstance(node.value, ast.List)
        ):
            continue
        broad = sorted(
            {
                e.value
                for e in node.value.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str) and _is_broad(e.value)
            }
        )
        if broad:
            scopes = ", ".join(repr(b) for b in broad)
            findings.append(
                ctx.finding(
                    node.value,
                    f"Over-broad MCP OAuth scope(s) {scopes}; a single stolen token then "
                    "grants wide access. Request the minimal scopes the caller needs.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-MCP-003",
    title="Over-broad / wildcard MCP OAuth scopes",
    category="MCP",
    pillar=Pillar.SECURITY,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=("A wildcard OAuth scope turns one stolen token into total blast radius."),
    standards=("CWE-250", "OWASP-LLM06"),
    remediation=REMEDIATION,
    detect=detect,
)
