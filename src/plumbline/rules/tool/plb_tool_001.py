"""PLB-TOOL-001 — Tool defined without an input schema / typed signature.

An untyped tool lets the model pass malformed arguments — a string where an int
was meant, a missing field, a wrong shape — which surfaces as a runtime crash or
silently wrong behavior deep inside the tool. A typed signature (or declared
`args_schema`) lets the framework validate and coerce arguments before the tool
runs. This is a reliability defect before it is a security one.

Consumes `TOOL_DEF` with `has_schema = Known(False)` (emitted by the langchain /
crewai adapters from the function signature or an `args_schema=` declaration).
"""

from __future__ import annotations

from ...model import Confidence, FindingDraft, Known, Pillar, SemanticTag, Severity
from .._harness_evidence import is_test_file
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Give every model-callable tool a typed signature or an explicit args schema.

Bad:
    @tool
    def lookup(order):              # untyped — the model can pass anything
        ...

Good:
    @tool
    def lookup(order_id: int) -> Order:   # typed; framework validates
        ...

    # or, with an explicit schema:
    StructuredTool.from_function(lookup, args_schema=LookupArgs)
"""


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    # Tools defined in test files are scaffolding, not the shipped agent surface,
    # and are routinely minimal/untyped on purpose — flagging them is noise
    # (real-repo FPs: crewAI's test suite). Concrete production tools still fire.
    if is_test_file(ctx.file):
        return findings
    for sn in ctx.semantics.by_tag(SemanticTag.TOOL_DEF):
        has_schema = sn.attrs.get("has_schema")
        if isinstance(has_schema, Known) and has_schema.value is False:
            name = sn.attrs.get("name")
            label = name.value if isinstance(name, Known) else "tool"
            findings.append(
                ctx.finding(
                    sn.node,
                    f"Tool {label!r} has no input schema or typed signature; the model "
                    "can pass malformed arguments that crash it at runtime.",
                )
            )
    return findings


RULE = Rule(
    id="PLB-TOOL-001",
    title="Tool defined without an input schema / typed signature",
    category="TOOL",
    pillar=Pillar.ARCHITECTURE,
    severity=Severity.MAJOR,
    confidence=Confidence.HIGH,  # measured 100% precision in /benchmark
    why_it_matters=(
        "An untyped tool lets the model pass malformed arguments that crash it at runtime."
    ),
    remediation=REMEDIATION,
    detect=detect,
)
