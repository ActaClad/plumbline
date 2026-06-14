"""PLB-SEC-003 — Untrusted content passed to a shell command.

Model output or untrusted input reaching `os.system`, `os.popen`, or a
`subprocess.*` call with `shell=True` is OS command injection. The argv-list form
(`subprocess.run([...])`, no shell) is safe and does not fire (see `_sinks`).
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, Severity
from .._sinks import shell_sink
from .._taint_flow import UNTRUSTED, first_label, witness_flow
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Never build a shell command from model output or untrusted input.

Bad:
    os.system(f"convert {llm_filename} out.png")     # command injection
    subprocess.run(cmd_from_model, shell=True)

Good:
    subprocess.run(["convert", validated_name, "out.png"])   # argv list, no shell
    # validate against an allow-list before use
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for node in ast.walk(ctx.tree.tree):
        if not isinstance(node, ast.Call):
            continue
        arg = shell_sink(ctx.tree, node)
        if arg is None:
            continue
        label = first_label(ctx.taint, arg, UNTRUSTED)
        if label is None:
            continue
        findings.append(
            ctx.finding(
                node,
                f"Untrusted {label.value} flows into a shell command — OS command injection.",
                code_flow=witness_flow(ctx.taint, ctx.file, arg, label, node, "run by the shell"),
            )
        )
    return findings


RULE = Rule(
    id="PLB-SEC-003",
    title="LLM output passed to a shell command",
    category="SEC",
    pillar=Pillar.SECURITY,
    severity=Severity.BLOCKER,
    confidence=Confidence.HIGH,  # measured 100% precision in /benchmark
    why_it_matters=(
        "Untrusted content in a shell command (os.system / shell=True) is OS command injection."
    ),
    standards=("CWE-78", "OWASP-LLM01"),
    remediation=REMEDIATION,
    detect=detect,
)
