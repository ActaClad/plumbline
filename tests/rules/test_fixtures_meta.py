"""Meta-test: every discovered rule has working fixtures (ADR-0005 D2).

This is the mechanical enforcement of "no rule without a failing fixture"
(CLAUDE.md §1.5). It runs the whole discovered rule set; adding a rule with
missing/broken fixtures fails here, in the author's PR.
"""

from __future__ import annotations

import pytest

from plumbline.rules.base import Rule, discover_rules
from tests.rules._harness import assert_fixtures

_RULES = discover_rules()


@pytest.mark.skipif(not _RULES, reason="no rules discovered yet")
@pytest.mark.parametrize("rule", _RULES, ids=[r.id for r in _RULES])
def test_rule_has_working_fixtures(rule: Rule) -> None:
    assert_fixtures(rule)
