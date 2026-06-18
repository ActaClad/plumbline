"""PLB-OUT-002 — LLM output used directly as control flow.

Branching on raw model output by string equality — `if response == "yes": …` —
is brittle and injectable: the model emits "Yes.", "sure, yes", or a translated
token and the branch silently misses. The robust pattern constrains the output
to an enum/schema and validates it *before* branching.

This is a taint rule over the existing LLM_OUTPUT label. Precision discipline
(CLAUDE.md §1.4) — it fires on the brittle pattern ONLY:

- Operator must be `==` / `!=` (single comparison). Membership (`in` / `not in`)
  is EXCLUDED — `if action in ALLOWED:` is the *validation fix*, not the defect.
- The other operand must be a **non-empty string literal**. This excludes the
  recommended empty/None guards (`if not out:`, `if out == "":`, `if out is
  None:`) — those are OUT-003 handling, and flagging them would punish exactly
  the behavior we want. It also excludes comparisons to variables (which may be
  validated values).
- The tainted operand must NOT be a structured response-envelope field
  (`item.type`, `.finish_reason`, `.role`, …). A value tainted LLM_OUTPUT is
  often the whole response object; comparing its discriminator field to a
  literal is correct schema dispatch, not content-branching. (Real-repo FP class
  — 9x on simonw/llm's response handler.)
"""

from __future__ import annotations

import ast

from ...core.taint import TaintLabel
from ...model import Confidence, FindingDraft, Pillar, Severity
from .._taint_flow import witness_flow
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Constrain the output to an enum/schema and validate it before branching — never
compare raw model text to an expected token.

Bad:
    answer = resp.choices[0].message.content
    if answer == "yes":
        approve()

Good:
    # ask for a structured/enum result, then validate membership
    answer = (resp.choices[0].message.content or "").strip().lower()
    if answer in {"yes", "no"}:
        ...
    else:
        handle_unexpected(answer)
"""

_MATCH_OPS = (ast.Eq, ast.NotEq)

# Structured response-envelope fields. A value tainted LLM_OUTPUT is often the
# whole response object; comparing one of THESE attributes to a literal
# (`if item.type == "function_call"`) is correct schema dispatch on an
# API-guaranteed discriminator, NOT brittle branching on generated text. Found
# 9x on simonw/llm's response handler — the real-repo FP class for this rule.
_METADATA_ATTRS = frozenset(
    {
        "type",
        "role",
        "finish_reason",
        "stop_reason",
        "status",
        "object",
        "index",
        "id",
        "name",
        "model",
    }
)


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for node in ast.walk(ctx.tree.tree):
        test = node.test if isinstance(node, ast.If | ast.While) else None
        if test is None:
            continue
        for cmp in _branching_compares(ctx, test):
            tainted = _tainted_operand(ctx, cmp)
            if tainted is None:
                continue
            findings.append(
                ctx.finding(
                    cmp,
                    "Control flow branches on raw LLM output by string equality; the "
                    "model rarely emits an exact token, so this is brittle and "
                    "injectable. Constrain the output to an enum/schema and validate it.",
                    code_flow=witness_flow(
                        ctx.taint,
                        ctx.file,
                        tainted,
                        TaintLabel.LLM_OUTPUT,
                        cmp,
                        "compared to a literal to drive control flow",
                    ),
                )
            )
    return findings


def _branching_compares(ctx: AnalysisContext, test: ast.expr) -> list[ast.Compare]:
    """Compares in the test that string-match against a non-empty literal: a
    single `==`/`!=` with a non-empty string-constant operand."""
    out: list[ast.Compare] = []
    for sub in ast.walk(test):
        if (
            isinstance(sub, ast.Compare)
            and len(sub.ops) == 1
            and isinstance(sub.ops[0], _MATCH_OPS)
            and any(_is_nonempty_str(o) for o in (sub.left, *sub.comparators))
        ):
            out.append(sub)
    return out


def _tainted_operand(ctx: AnalysisContext, cmp: ast.Compare) -> ast.expr | None:
    for operand in (cmp.left, *cmp.comparators):
        if _is_nonempty_str(operand) or _is_metadata_field(operand):
            continue  # the literal side, or a structured discriminator — not the defect
        if ctx.taint.is_tainted(operand, TaintLabel.LLM_OUTPUT):
            return operand
    return None


def _is_metadata_field(node: ast.expr) -> bool:
    """`x.type`, `item.finish_reason`, … — a structured response-envelope field,
    not generated content. Branching on it is schema dispatch, not the defect."""
    return isinstance(node, ast.Attribute) and node.attr in _METADATA_ATTRS


def _is_nonempty_str(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value != ""


RULE = Rule(
    id="PLB-OUT-002",
    title="LLM output used directly as control flow",
    category="OUT",
    pillar=Pillar.RELIABILITY,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        'Branching on raw model output (`if response == "yes"`) is brittle and injectable.'
    ),
    remediation=REMEDIATION,
    detect=detect,
)
