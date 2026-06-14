"""PLB-GOV-001 fixtures fire/stay-silent."""

from __future__ import annotations

from plumbline.rules.gov.plb_gov_001 import RULE
from tests.rules._harness import assert_fixtures


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-GOV-001"
