"""PLB-EVAL-003 — Prompt/model changes not gated by evaluation in CI.

Reframed statically (no VCS diff): the repo ships LLM/agent code and HAS a CI
pipeline, but that pipeline never invokes a test/eval suite — so prompt and model
changes merge without any automated behavioral check.

This is a **sanctioned grep rule** (CLAUDE.md §1.2, `grep_rule=True`): dataflow
does not apply to CI YAML, so it scans the *text* of recognized CI config files
(ADR-0013 non-Python evidence channel) for a test/eval invocation token. Ships
Medium/advisory — token matching is heuristic, and it only adds signal over
EVAL-001 when evals exist but CI doesn't run them. See `docs/specs/harness-rules.md`.
"""

from __future__ import annotations

from ...model import Confidence, FindingDraft, Pillar, Severity
from .._harness_evidence import SCOPE_CAVEAT, agentic_anchor
from ..base import ProjectContext, Rule, RuleScope

REMEDIATION = """\
Run your test/eval suite in CI so model and prompt changes are gated.

# .github/workflows/ci.yml
- run: pytest                     # or: tox / nox / deepeval / your eval target

Fail the pipeline on regressions — that is what turns "we have evals" into
"evals actually protect production".
"""

# Tokens that mean "CI runs tests/evals". Lowercased substring match (grep rule).
_EVAL_INVOCATION_TOKENS: tuple[str, ...] = (
    "pytest",
    "tox",
    "nox",
    "unittest",
    "deepeval",
    "ragas",
    "promptfoo",
    "inspect eval",
    "make test",
    "make eval",
    "npm test",
    "run: test",
    "evaluate",
    "/evals",
    "eval.py",
)


def detect(ctx: ProjectContext) -> list[FindingDraft]:
    anchor = agentic_anchor(ctx.files)
    if anchor is None:
        return []  # no LLM/agent code -> N/A
    if not ctx.evidence.has_ci:
        return []  # no CI at all -> "no eval suite" is EVAL-001's job, not this one
    if any(_invokes_eval(text) for text in ctx.evidence.ci_files.values()):
        return []
    file, node = anchor
    return [
        ctx.finding(
            file,
            node,
            "This project has a CI pipeline but it never runs a test/eval suite; "
            "prompt and model changes merge with no automated behavioral check." + SCOPE_CAVEAT,
        )
    ]


def _invokes_eval(ci_text: str) -> bool:
    lowered = ci_text.lower()
    return any(tok in lowered for tok in _EVAL_INVOCATION_TOKENS)


RULE = Rule(
    id="PLB-EVAL-003",
    title="Prompt/model changes not gated by evaluation in CI",
    category="EVAL",
    pillar=Pillar.HARNESS,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "A CI pipeline that never runs evals lets prompt/model regressions reach production."
    ),
    standards=("NIST-AI-RMF:MEASURE",),
    remediation=REMEDIATION,
    detect=detect,
    scope=RuleScope.PROJECT,
    grep_rule=True,
)
