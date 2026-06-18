"""PLB-PRM-003 — No system prompt defined.

A chat completion built with only user/assistant turns and no system prompt
leaves the model's role, constraints, and refusal behavior undefined — behavior
drifts and the model is more steerable by user input. Establishing a system
prompt is the baseline of prompt hygiene.

Precision discipline (CLAUDE.md §1.4) — fires ONLY when the message construction
is fully inspectable and provably has no system prompt:

- `messages=` must be an **inline list literal** whose every element is a dict
  literal. If messages is a variable, or any element is non-literal, the roles
  cannot be seen — skip (no fire), never guess.
- A system prompt is recognized either as a message with role `system` /
  `developer` (OpenAI style) OR a top-level `system=` kwarg (Anthropic style),
  so the rule is provider-agnostic without branching on provider.

Minor/advisory: a missing system prompt is a maturity signal, not a failure.
"""

from __future__ import annotations

import ast

from ...model import Confidence, FindingDraft, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Add a system prompt establishing the model's role, constraints, and refusal
behavior — the baseline of prompt hygiene.

Bad:
    client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )

Good:
    client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a support agent. Refuse off-topic requests."},
            {"role": "user", "content": prompt},
        ],
    )
    # Anthropic: pass a top-level `system=` argument.
"""

_SYSTEM_ROLES = frozenset({"system", "developer"})


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        call = sn.node
        if not isinstance(call, ast.Call):
            continue
        messages = _keyword(call, "messages")
        if not isinstance(messages, ast.List) or not messages.elts:
            continue  # not an inspectable inline message list — do not guess
        if _has_keyword(call, "system"):
            continue  # Anthropic-style system prompt
        if not all(isinstance(e, ast.Dict) for e in messages.elts):
            continue  # an opaque element could be the system message — skip
        if any(_is_system_message(e) for e in messages.elts):
            continue
        findings.append(
            ctx.finding(
                call,
                "Chat completion has no system prompt; the model's role, constraints, "
                "and refusal behavior are undefined. Add a system message (or, for "
                "Anthropic, a `system=` argument).",
            )
        )
    return findings


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _has_keyword(call: ast.Call, name: str) -> bool:
    return any(kw.arg == name for kw in call.keywords)


def _is_system_message(node: ast.expr) -> bool:
    if not isinstance(node, ast.Dict):
        return False
    for key, value in zip(node.keys, node.values, strict=False):
        if (
            isinstance(key, ast.Constant)
            and key.value == "role"
            and isinstance(value, ast.Constant)
            and value.value in _SYSTEM_ROLES
        ):
            return True
    return False


RULE = Rule(
    id="PLB-PRM-003",
    title="No system prompt defined",
    category="PRM",
    pillar=Pillar.ARCHITECTURE,
    severity=Severity.MINOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "A chat call with no system prompt leaves the model's role, constraints, and "
        "refusal behavior undefined."
    ),
    remediation=REMEDIATION,
    detect=detect,
)
