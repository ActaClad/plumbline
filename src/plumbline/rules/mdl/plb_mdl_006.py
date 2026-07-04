"""PLB-MDL-006 — Removed sampling parameter passed to a reasoning model.

Reasoning/thinking models (OpenAI o-series & GPT-5; Anthropic Opus 4.7/4.8 &
Fable-5) **removed** the sampling parameters `temperature`/`top_p`/`top_k` from
their API — passing any of them is not ignored, it returns an HTTP 400 on *every*
call. Code that worked on a chat model breaks the instant the model string is
switched to a reasoning model.

Detection reads the adapter-resolved `model` (tri-state `Known`, so a model pinned
in a single-assignment variable is caught, like MDL-002) and matches it against the
curated `SAMPLING_UNSUPPORTED` table (ADR-0017/0018). The offending param is
detected by **provable presence** — an explicit keyword on the call node — so a
param spread via `**kwargs` is never flagged (precision over recall; CLAUDE.md
§1.4). Ships **Medium/advisory** until a `/benchmark` precision pass (ADR-0018).
"""

from __future__ import annotations

import ast

from ...data.reasoning_models import SAMPLING_UNSUPPORTED
from ...model import Confidence, FindingDraft, Known, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Reasoning models reject sampling parameters (temperature/top_p/top_k) — the call
returns HTTP 400 on every invocation. Remove them; a reasoning model self-regulates
its sampling, and you steer effort with reasoning-effort controls instead.

Bad:
    client.chat.completions.create(model="o3", messages=msgs, temperature=0.7)  # 400

Good:
    client.chat.completions.create(model="o3", messages=msgs)   # let the model reason
"""


def _explicit_keywords(node: ast.AST) -> set[str]:
    """Keyword arg NAMES provably present on the call (excludes `**kwargs`)."""
    if not isinstance(node, ast.Call):
        return set()
    return {kw.arg for kw in node.keywords if kw.arg is not None}


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for sn in ctx.semantics.by_tag(SemanticTag.LLM_CALL):
        model = sn.attrs.get("model")
        if not (isinstance(model, Known) and isinstance(model.value, str)):
            continue
        removed = SAMPLING_UNSUPPORTED.get(model.value)
        if not removed:
            continue
        hit = sorted(removed & _explicit_keywords(sn.node))
        if not hit:
            continue
        params = ", ".join(hit)
        findings.append(
            ctx.finding(
                sn.node,
                f"Model {model.value!r} does not accept {params}; reasoning models "
                "removed sampling parameters, so the call returns HTTP 400 on every "
                "invocation. Remove them.",
            )
        )
    return findings


RULE = Rule(
    id="PLB-MDL-006",
    title="Removed sampling parameter passed to a reasoning model",
    category="MDL",
    pillar=Pillar.RELIABILITY,
    # Every-call outage → Critical blast radius, but Medium/advisory until a
    # real-repo precision pass measures it (ADR-0018; CLAUDE.md §1.3).
    severity=Severity.CRITICAL,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "A sampling param on a reasoning model is a guaranteed HTTP 400 — the call "
        "fails on every invocation, not intermittently."
    ),
    standards=("CWE-628", "OWASP-LLM10"),
    remediation=REMEDIATION,
    detect=detect,
)
