"""Eval + tracing harness for the flat corpus 'project'. The corpus represents a
project that HAS a harness but ships the demonstrated file-level defects, so the
project-scope absence rules (EVAL-001, OBS-001) stay silent here and are measured
via their directory fixtures instead (ADR-0010 D3). Named zz_ so it sorts last
and never becomes a finding anchor."""
import deepeval  # eval-framework signal -> EVAL-001 silent
import opentelemetry  # tracing signal -> OBS-001 silent
