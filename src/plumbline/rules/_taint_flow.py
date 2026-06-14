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
