"""PLB-TOOL-003 — Tool with no error handling / can crash the agent run.

A tool whose body makes an external call (HTTP, shell, or a model/embedding/
retriever call) but has no error handling lets that call's exception propagate
out of the tool. In an agent loop that aborts the *whole run* instead of letting
the agent observe a structured error and recover — a transient 500 from one tool
takes down the entire task.

Sibling of RES-005 in shape, inverted: RES-005 fires on a try that *swallows*;
this fires on a tool that makes an external call with *no* try at all.

Precision discipline (CLAUDE.md §1.4):
- Only `@tool`-decorated functions (TOOL_DEF whose node is a function) are
  inspected — their body is right there. Constructor-style tools
  (`StructuredTool.from_function(fn)`) point at a function defined elsewhere and
  are not chased here (precision over recall).
- "External call" is restricted to calls that genuinely reach outside the
  process and routinely fail: HTTP (requests/httpx/urllib/aiohttp), shell, and
  semantically-tagged model/embedding/retriever calls. Pure computation never
  fires.
- The presence of *any* `try` anywhere in the function counts as error handling
  and silences the rule — the conservative bias (we would rather miss a
  partially-guarded tool than flag a guarded one). Advisory (Medium).
- Tools in test files are scaffolding and are skipped, as in TOOL-001.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Known, Pillar, SemanticTag, Severity
from .._harness_evidence import is_test_file
from .._sinks import http_url_sink, shell_sink
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Handle errors inside the tool and return a structured error the agent can reason
about — never let a tool's exception abort the whole run.

Bad:
    @tool
    def fetch_order(order_id: int) -> dict:
        resp = requests.get(f"https://api/orders/{order_id}")
        return resp.json()                 # raises straight out of the tool

Good:
    @tool
    def fetch_order(order_id: int) -> dict:
        try:
            resp = requests.get(f"https://api/orders/{order_id}", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            return {"error": str(exc)}      # the agent can observe and recover
"""

# Semantic calls that reach outside the process (in addition to the AST-level
# HTTP/shell sinks). A tool that calls the model or a retriever depends on a
# remote service that routinely fails.
_EXTERNAL_TAGS = (
    SemanticTag.LLM_CALL,
    SemanticTag.EMBEDDING_CALL,
    SemanticTag.RETRIEVER_CALL,
    SemanticTag.HTTP_CALL,
)


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    if is_test_file(ctx.file):
        return findings
    external_nodes = {sn.node for tag in _EXTERNAL_TAGS for sn in ctx.semantics.by_tag(tag)}
    for sn in ctx.semantics.by_tag(SemanticTag.TOOL_DEF):
        fn = sn.node
        if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
            continue  # constructor-style tool — body is elsewhere
        if _has_try(fn):
            continue  # has some error handling — conservatively silent
        if not _has_external_call(ctx, fn, external_nodes):
            continue  # pure computation — nothing to guard
        name = sn.attrs.get("name")
        label = name.value if isinstance(name, Known) else fn.name
        findings.append(
            ctx.finding(
                fn,
                f"Tool {label!r} makes an external call with no error handling; an "
                "exception propagates out of the tool and aborts the whole agent run "
                "instead of degrading to a structured error.",
            )
        )
    return findings


def _has_try(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(isinstance(n, ast.Try) for n in ast.walk(fn))


def _has_external_call(
    ctx: AnalysisContext,
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    external_nodes: set[ast.AST],
) -> bool:
    for n in ast.walk(fn):
        if n in external_nodes:
            return True
        if isinstance(n, ast.Call) and (
            http_url_sink(n) is not None or shell_sink(ctx.tree, n) is not None
        ):
            return True
    return False


RULE = Rule(
    id="PLB-TOOL-003",
    title="Tool with no error handling can crash the agent run",
    category="TOOL",
    pillar=Pillar.ARCHITECTURE,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "An unhandled exception inside a tool aborts the whole agent run instead of "
        "degrading gracefully."
    ),
    remediation=REMEDIATION,
    detect=detect,
)
