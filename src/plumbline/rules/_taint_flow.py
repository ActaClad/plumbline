"""Build a Finding `code_flow` from a taint witness (ADR-0014).

The taint engine records, per `(node, label)`, the witness path that carried the
label to that node (`TaintView.witness`). A taint rule turns that path plus its
sink location into an ordered source→…→sink `code_flow` for SARIF codeFlows.
Shared by OUT-001 and the SEC taint rules.
"""

from __future__ import annotations

import ast

from ..core.taint import TaintLabel, TaintView
from ..model import CodeFlowStep

#: Labels that denote attacker-controllable / untrusted content reaching a sink.
#: (PII is sensitive, not untrusted — handled separately by GOV rules.)
UNTRUSTED: tuple[TaintLabel, ...] = (
    TaintLabel.LLM_OUTPUT,
    TaintLabel.USER_INPUT,
    TaintLabel.TOOL_RESULT,
    TaintLabel.RETRIEVED_CONTENT,
    TaintLabel.EXTERNAL_HTTP,
)


def first_label(
    taint: TaintView, node: ast.AST, labels: tuple[TaintLabel, ...]
) -> TaintLabel | None:
    """The first of `labels` (in priority order) that taints `node`, else None.
    Lets a sink rule fire on any untrusted source while naming a concrete one."""
    present = taint.labels(node)
    return next((label for label in labels if label in present), None)


def witness_flow(
    taint: TaintView,
    file: str,
    tainted_node: ast.AST,
    label: TaintLabel,
    sink_node: ast.AST,
    sink_message: str,
) -> tuple[CodeFlowStep, ...]:
    """source → … → sink, in order. The witness hops describe how `label`
    reached `tainted_node`; the final step is the dangerous sink itself."""
    steps = [
        CodeFlowStep(file, hop.line, hop.column, hop.description)
        for hop in taint.witness(tainted_node, label)
    ]
    steps.append(
        CodeFlowStep(
            file,
            getattr(sink_node, "lineno", 0),
            getattr(sink_node, "col_offset", None),
            sink_message,
        )
    )
    return tuple(steps)
