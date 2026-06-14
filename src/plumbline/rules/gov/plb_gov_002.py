"""PLB-GOV-002 — Full prompts/responses or PII logged.

Logging raw model responses or personal data at info/debug copies sensitive
content into log sinks (often shipped to third-party log aggregators) with none
of the access controls of the primary store. Taint rule: fires when LLM output or
PII reaches a logging call (`logger.info(...)`, `logging.debug(...)`, `print`).
"""

from __future__ import annotations

import ast

from ...core.taint import TaintLabel
from ...model import Confidence, FindingDraft, Pillar, Severity
from .._sinks import log_args
from .._taint_flow import first_label, witness_flow
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Log metadata and identifiers, not raw content.

Bad:
    logger.info("model said: %s", response_text)
    logger.debug(user_email)

Good:
    logger.info("completion ok", extra={"run_id": run_id, "tokens": usage.total})
"""

_SENSITIVE: tuple[TaintLabel, ...] = (TaintLabel.LLM_OUTPUT, TaintLabel.PII)


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for node in ast.walk(ctx.tree.tree):
        if not isinstance(node, ast.Call):
            continue
        for arg in log_args(node):
            label = first_label(ctx.taint, arg, _SENSITIVE)
            if label is None:
                continue
            what = "the model response" if label is TaintLabel.LLM_OUTPUT else "PII"
            findings.append(
                ctx.finding(
                    node,
                    f"{what} is written to a log sink; sensitive content lands in logs with "
                    "weaker access controls than the primary store.",
                    code_flow=witness_flow(
                        ctx.taint, ctx.file, arg, label, node, "written to a log"
                    ),
                )
            )
            break
    return findings


RULE = Rule(
    id="PLB-GOV-002",
    title="Full prompts/responses logged at info/debug",
    category="GOV",
    pillar=Pillar.SECURITY,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "Logging raw model responses or PII copies sensitive content into weakly-controlled logs."
    ),
    standards=("NIST-AI-RMF:MAP",),
    remediation=REMEDIATION,
    detect=detect,
)
