"""PLB-OBS-001 — No tracing/instrumentation configured (project-scope).

An LLM/agent app with no tracing is undiagnosable in production: when a chain
misbehaves, there is no record of the prompts, tool calls, or latencies to debug
from. Project-scope absence rule (ADR-0010).

The shakiest harness rule, and it says so in its own finding: tracing is often
enabled *out of code* — `LANGCHAIN_TRACING_V2=true`, `opentelemetry-instrument`,
`OTEL_*` env vars — which static analysis cannot see. So detection is broad (any
observability SDK, framework callback, or in-code env-var reference ⇒ silent),
the finding self-discloses the env-var blind spot, and it ships Medium/advisory.
See `docs/specs/harness-rules.md` §OBS-001.
"""

from __future__ import annotations

from ...model import Confidence, FindingDraft, Pillar, Severity
from .._harness_evidence import (
    SCOPE_CAVEAT,
    agentic_anchor,
    imported_modules,
    string_constants,
)
from ..base import ProjectContext, Rule, RuleScope

REMEDIATION = """\
Instrument the app so production runs are traceable.

- An observability SDK: OpenTelemetry, LangSmith, Langfuse, Phoenix/Arize,
  Logfire, Helicone, Traceloop, …
- or the framework's tracing callbacks (LangChain callbacks, CrewAI telemetry).

If you already enable tracing via environment variables
(LANGCHAIN_TRACING_V2=true, OTEL_* auto-instrumentation), this finding does not
apply — Plumbline cannot see env-var activation; ignore or suppress it.
"""

# Observability SDK roots. Broad on purpose (absence rule errs toward silence).
_TRACE_ROOTS = frozenset(
    {
        "opentelemetry",
        "langsmith",
        "langfuse",
        "phoenix",
        "arize",
        "helicone",
        "traceloop",
        "logfire",
        "wandb",
        "weave",
        "braintrust",
        "mlflow",
        "openinference",
        "openllmetry",
    }
)
# In-code references that show tracing intent even without an SDK import.
_TRACE_ENV = ("LANGCHAIN_TRACING", "OTEL_", "LANGSMITH_")


def detect(ctx: ProjectContext) -> list[FindingDraft]:
    anchor = agentic_anchor(ctx.files)
    if anchor is None:
        return []
    if _has_tracing_evidence(ctx):
        return []
    file, node = anchor
    return [
        ctx.finding(
            file,
            node,
            "This project ships LLM/agent code with no in-code tracing or "
            "instrumentation; production failures will be undiagnosable. (If you "
            "enable tracing via env vars / auto-instrumentation, ignore this.)" + SCOPE_CAVEAT,
        )
    ]


def _has_tracing_evidence(ctx: ProjectContext) -> bool:
    for fa in ctx.files:
        modules = imported_modules(fa)
        for m in modules:
            root = m.split(".")[0]
            if root in _TRACE_ROOTS:
                return True
            # framework tracing callbacks (langchain.callbacks.tracers, …)
            if "callbacks" in m or "tracer" in m or "tracing" in m:
                return True
        if any(any(env in s for env in _TRACE_ENV) for s in string_constants(fa)):
            return True
    return False


RULE = Rule(
    id="PLB-OBS-001",
    title="No tracing/instrumentation configured",
    category="OBS",
    pillar=Pillar.HARNESS,
    severity=Severity.MAJOR,
    confidence=Confidence.MEDIUM,
    why_it_matters=(
        "An LLM/agent app with no tracing is unobservable in production — failures can't be traced."
    ),
    standards=("NIST-AI-RMF:MEASURE",),
    remediation=REMEDIATION,
    detect=detect,
    scope=RuleScope.PROJECT,
)
