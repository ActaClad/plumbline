"""PLB-SEC-004 — Hardcoded API key or secret.

The one sanctioned **pattern/grep rule** in the catalog (CLAUDE.md §1.2,
`grep_rule=True`): dataflow does not apply to "a secret literal sits in source".
To avoid the false positives that plague secret scanners, it fires only on:

1. a string literal **assigned to a secret-named target** (`api_key = "…"`) that
   is not an obvious placeholder, or
2. a string literal matching a **known provider key pattern** (`sk-…`, `AKIA…`,
   `ghp_…`, Slack tokens).

It deliberately does NOT fire on env-var *names* (`os.getenv("API_KEY")` — the
literal is the variable name, not a secret) or on placeholders
(`"your-api-key-here"`, `"changeme"`, `"<token>"`, empty strings).
"""

from __future__ import annotations

import ast
import re

from ...model import Confidence, FindingDraft, Pillar, Severity
from .._harness_evidence import is_test_file
from ..base import AnalysisContext, Rule

REMEDIATION = """\
Never commit secrets. Load them at runtime from the environment or a secret
manager.

Bad:
    OPENAI_API_KEY = "sk-abc123...realkey..."

Good:
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
"""

# Target names (case-insensitive, suffix-matched) that denote a secret. Bare
# `token` and `secret` are deliberately EXCLUDED — they are wildly overloaded
# (contextvar tokens, sentinel/label strings, CSRF/pagination tokens: real-repo
# FPs `bearer_token="bearerToken"`, `STDERR_NULL_TOKEN`, contextvar tokens). Only
# the specific compound names are high-signal; a real key in a `token` var is
# still caught by the provider-pattern path below regardless of its name.
_SECRET_NAMES: frozenset[str] = frozenset(
    {
        "api_key",
        "apikey",
        "secret_key",
        "client_secret",
        "access_token",
        "auth_token",
        "password",
        "passwd",
        "private_key",
    }
)
# Real provider key shapes — these are self-validating (length/charset).
_PROVIDER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI / Anthropic style
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"ghp_[A-Za-z0-9]{36}"),  # GitHub PAT
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),  # Google API key
)
# Obvious non-secrets — never flag these. Anchored shapes…
_PLACEHOLDER = re.compile(
    r"^\s*$|^(x+|\.+|-+|none|null|todo|changeme|change-me|example|placeholder|dummy|fake|test|"
    r"your[-_ ].*|<.*>|\$\{.*\}|\{\{.*\}\})\s*$",
    re.IGNORECASE,
)
# …plus a dummy/test marker ANYWHERE in the value (substring). Real-repo FPs were
# test fixtures: `access_token = "test_token"`, etc. (found scanning crewAI).
_DUMMY_SUBSTRINGS: tuple[str, ...] = (
    "test",
    "fake",
    "dummy",
    "example",
    "sample",
    "placeholder",
    "changeme",
    "redacted",
    "your-",
    "your_",
    "xxxx",
    "foobar",
)
_MIN_SECRET_LEN = 8
# A real secret is high-entropy. Reject low-diversity fakes by ABSOLUTE distinct
# alphanumeric count — never a ratio: a 64-char hex key has a low distinct/len
# ratio but ~16 distinct chars, so a ratio test would false-NEGATIVE real keys.
_MIN_DISTINCT_ALNUM = 5


def _is_placeholder(value: str) -> bool:
    low = value.strip().lower()
    return bool(_PLACEHOLDER.match(value)) or any(s in low for s in _DUMMY_SUBSTRINGS)


def _distinct_alnum(value: str) -> int:
    return len({c for c in value.lower() if c.isalnum()})


def detect(ctx: AnalysisContext) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    # The secret-NAMED-variable heuristic is fuzzy (a `*_token` may be a contextvar
    # token, a CSRF token, …). Test files are dominated by such fixtures, so the
    # heuristic is suppressed there (real-repo FPs: crewAI's contextvar tests). A
    # real provider-pattern key is still flagged everywhere, including in tests.
    in_test = is_test_file(ctx.file)
    for node in ast.walk(ctx.tree.tree):
        # 1. literal assigned to a secret-named target (skipped in test files)
        if not in_test and isinstance(node, ast.Assign | ast.AnnAssign):
            value = node.value
            if (
                isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and any(_is_secret_name(n) for n in _targets(node))
                and _looks_secret(value.value)
            ):
                findings.append(_finding(ctx, node, "a secret-named variable"))
                continue
        # 2. a provider key pattern anywhere
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and not _is_placeholder(node.value)
            and _matches_provider(node.value)
        ):
            findings.append(_finding(ctx, node, "a provider key pattern"))
    return findings


def _finding(ctx: AnalysisContext, node: ast.AST, why: str) -> FindingDraft:
    return ctx.finding(
        node,
        f"Hardcoded secret detected ({why}); load it from the environment or a secret "
        "manager instead of committing it.",
    )


def _targets(node: ast.Assign | ast.AnnAssign) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return [t.id for t in targets if isinstance(t, ast.Name)]


def _is_secret_name(name: str) -> bool:
    low = name.lower()
    return low in _SECRET_NAMES or any(
        low.endswith("_" + s) or low.endswith(s) for s in _SECRET_NAMES
    )


def _looks_secret(value: str) -> bool:
    return (
        len(value) >= _MIN_SECRET_LEN
        and not _is_placeholder(value)
        and _distinct_alnum(value) >= _MIN_DISTINCT_ALNUM
    )


def _matches_provider(value: str) -> bool:
    return any(p.search(value) for p in _PROVIDER_PATTERNS)


RULE = Rule(
    id="PLB-SEC-004",
    title="Hardcoded API key or secret",
    category="SEC",
    pillar=Pillar.SECURITY,
    severity=Severity.BLOCKER,
    confidence=Confidence.HIGH,  # measured 100% precision in /benchmark
    why_it_matters=(
        "A committed API key or secret is an immediate credential leak to anyone with repo access."
    ),
    standards=("CWE-798",),
    remediation=REMEDIATION,
    detect=detect,
    grep_rule=True,
)
