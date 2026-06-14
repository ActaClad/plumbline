"""PLB-SEC-002 — Untrusted content passed to eval/exec/compile.

Executing model output (or any untrusted input) as code is remote code execution:
a single crafted generation or user string runs arbitrary Python in your process.
Taint rule — fires when an untrusted source actually reaches `eval`/`exec`/
`compile`. Among the SEC rules this has the lowest false-positive surface:
eval/exec of untrusted data is essentially never legitimate.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, Severity
from .._sinks import code_exec_sink
from .._taint_flow import UNTRUSTED, first_label, witness_flow
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Never execute model output or untrusted input. There is almost always a safe
alternative:

Bad:
    plan = llm.generate(...)
    result = eval(plan)              # arbitrary code execution

Good:
    # parse to a constrained structure instead of executing
    action = json.loads(plan)        # then dispatch on a fixed allow-list
    handler = ALLOWED_ACTIONS[action["name"]]

If you genuinely must run generated code, do it in a sandboxed, resource-limited
subprocess with no host access — never in-process.
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for node in ast.walk(ctx.tree.tree):
        if not isinstance(node, ast.Call):
            continue
        arg = code_exec_sink(node)
        if arg is None:
            continue
        label = first_label(ctx.taint, arg, UNTRUSTED)
        if label is None:
            continue
        fn = node.func.id if isinstance(node.func, ast.Name) else "eval"
        findings.append(
            ctx.finding(
                node,
                f"Untrusted {label.value} is executed as code by {fn}() — arbitrary "
                "code execution.",
                code_flow=witness_flow(
                    ctx.taint, ctx.file, arg, label, node, f"executed as code by {fn}()"
                ),
            )
        )
    return findings


RULE = Rule(
    id="PLB-SEC-002",
    title="LLM output passed to eval/exec/compile",
    category="SEC",
    pillar=Pillar.SECURITY,
    severity=Severity.BLOCKER,
    confidence=Confidence.HIGH,  # measured 100% precision in /benchmark
    why_it_matters=(
        "Executing model output or untrusted input as code is in-process remote code execution."
    ),
    standards=("CWE-95", "OWASP-LLM01"),
    remediation=REMEDIATION,
    detect=detect,
)
