"""PLB-MDL-002 — Deprecated / sunset model identifier.

A model id that the provider has retired (or scheduled for sunset) is a
*scheduled production outage*: the call works today and starts returning errors
on the cutoff date. Catching it statically turns a future incident into a
present-day fix.

Detection consumes the adapter-resolved `model` attribute (tri-state `Known`) on
LLM_CALL / LLM_CLIENT_CREATE / EMBEDDING_CALL nodes and matches it by **exact
string equality** against the curated `DEPRECATED_MODELS` table (ADR-0017). Using
the resolved attr (not a raw literal scan) means it also catches a model pinned
in a single-assignment variable (`MODEL = "claude-2"; create(model=MODEL)`).

Confidence is **Medium/advisory** (ADR-0017): detection is deterministic, but the
rule has no measured real-repo precision yet, so it informs without gating — it
graduates to High only after a real-repo precision pass (CLAUDE.md §1.3).
"""

from __future__ import annotations

from ...data.deprecated_models import DEPRECATED_MODELS
from ...model import Confidence, FindingDraft, Known, Pillar, SemanticTag, Severity
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Migrate off the deprecated model and re-run your evaluations after switching —
a retired identifier starts failing on the provider's cutoff date.

Bad:
    client.chat.completions.create(model="gpt-3.5-turbo-0301", ...)

Good:
    client.chat.completions.create(model="gpt-4o-mini", ...)   # current, supported
"""

# LLM_CLIENT_CREATE carries the model for frameworks that pin it at construction
# (LangChain `ChatOpenAI(model=...)`); LLM_CALL carries it for the raw SDK; the
# embedding path has its own model.
_MODEL_TAGS = (SemanticTag.LLM_CALL, SemanticTag.LLM_CLIENT_CREATE, SemanticTag.EMBEDDING_CALL)


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for tag in _MODEL_TAGS:
        for sn in ctx.semantics.by_tag(tag):
            model = sn.attrs.get("model")
            if not (isinstance(model, Known) and isinstance(model.value, str)):
                continue
            note = DEPRECATED_MODELS.get(model.value)
            if note is None:
                continue
            findings.append(
                ctx.finding(
                    sn.node,
                    f"Model {model.value!r} is deprecated/sunset ({note}); it is a "
                    "scheduled outage — the call starts failing on the provider's "
                    "cutoff date. Migrate to a supported model.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-MDL-002",
    title="Deprecated or sunset model identifier",
    category="MDL",
    pillar=Pillar.RELIABILITY,
    # Critical blast radius (a scheduled outage), but Medium/advisory until a
    # real-repo precision pass measures it (ADR-0017; CLAUDE.md §1.3). Deterministic
    # detection does not by itself earn the High/gating bar.
    severity=Severity.CRITICAL,
    confidence=Confidence.MEDIUM,
    why_it_matters=("A deprecated model string is a scheduled production outage."),
    remediation=REMEDIATION,
    detect=detect,
)
