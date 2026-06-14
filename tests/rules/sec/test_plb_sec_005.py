"""PLB-SEC-005 fixtures fire/stay-silent (safe forms must not fire)."""

from __future__ import annotations

from plumbline.rules.sec.plb_sec_005 import RULE
from tests.rules._harness import assert_fixtures


def test_fixtures_fire_and_stay_silent() -> None:
    assert_fixtures(RULE)


def test_metadata() -> None:
    assert RULE.id == "PLB-SEC-005"
    assert RULE.pillar.name == "SECURITY"
