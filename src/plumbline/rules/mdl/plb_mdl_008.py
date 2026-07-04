"""PLB-MDL-008 — OpenAI reasoning model uses `max_tokens`, not `max_completion_tokens`.

OpenAI's o-series and GPT-5 reasoning models reject `max_tokens` on Chat
Completions — the required parameter is `max_completion_tokens`. A call carried
over from a chat model returns HTTP 400 on every invocation ("Unsupported
parameter: 'max_tokens' … use 'max_completion_tokens' instead").

Detection reads the adapter-resolved `model` (tri-state `Known`, so a pinned
variable is caught) and matches it against `OPENAI_REASONING_MODELS`
(ADR-0017/0018); `max_tokens` is detected by **provable presence** as an explicit
keyword, so a `**kwargs` spread is never flagged. Anthropic models are absent from
the table — they *require* `max_tokens`, so flagging it there would be a false
positive. Ships **Medium/advisory** until a `/benchmark` precision pass.
"""

from __future__ import annotations

import ast

from ...data.reasoning_models import OPENAI_REASONING_MODELS
from ...model import Confidence, FindingDraft, Known, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
OpenAI reasoning models reject `max_tokens` on Chat Completions — the call 400s.
Rename the argument to `max_completion_tokens`.

Bad:
    client.chat.completions.create(model="o3", messages=msgs, max_tokens=2000)  # 400

Good:
    client.chat.completions.create(model="o3", messages=msgs, max_completion_tokens=2000)
"""


def _has_explicit_keyword(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Call) and any(kw.arg == name for kw in node.keywords)


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        model = sn.attrs.get("model")
        if not (isinstance(model, Known) and isinstance(model.value, str)):
            continue
        if model.value not in OPENAI_REASONING_MODELS:
            continue
        if not _has_explicit_keyword(sn.node, "max_tokens"):
            continue
        findings.append(
            ctx.finding(
                sn.node,
                f"OpenAI reasoning model {model.value!r} rejects 'max_tokens' on Chat "
                "Completions; use 'max_completion_tokens'. The call returns HTTP 400 on "
                "every invocation.",
            )
        )
    return findings


RULE = Rule(
    id="PLB-MDL-008",
    title="OpenAI reasoning model uses max_tokens not max_completion_tokens",
    category="MDL",
    pillar=Pillar.RELIABILITY,
    severity=Severity.CRITICAL,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "`max_tokens` on an OpenAI reasoning model is a guaranteed HTTP 400 — the "
        "wrong parameter name fails every call."
    ),
    standards=("CWE-628", "OWASP-LLM10"),
    remediation=REMEDIATION,
    detect=detect,
)
