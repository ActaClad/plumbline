"""Tests for the Finding model and fingerprint algorithm (ADR-0002)."""

from __future__ import annotations

import dataclasses

from plumbline.model import (
    ABSENT,
    UNKNOWN,
    Confidence,
    FindingDraft,
    Known,
    Pillar,
    Severity,
    assign_fingerprints,
    compute_fingerprint,
    finding_sort_key,
    normalize_anchor,
)


def _draft(rule_id: str, file: str, anchor: str, line: int, column: int = 0) -> FindingDraft:
    return FindingDraft(
        rule_id=rule_id,
        title="t",
        category=rule_id.split("-")[1],
        pillar=Pillar.RELIABILITY,
        severity=Severity.BLOCKER,
        confidence=Confidence.HIGH,
        message="m",
        why_it_matters="w",
        file=file,
        line=line,
        column=column,
        end_line=None,
        snippet=None,
        standards=(),
        remediation="r",
        anchor=anchor,
    )


# --- enums --------------------------------------------------------------------


def test_severity_ordering_is_total_and_correct() -> None:
    assert Severity.BLOCKER > Severity.CRITICAL > Severity.MAJOR > Severity.MINOR > Severity.INFO


def test_confidence_ordering() -> None:
    assert Confidence.HIGH > Confidence.MEDIUM > Confidence.LOW


def test_pillar_display_strings() -> None:
    assert Pillar.ARCHITECTURE.display == "Architecture & Agentic Maturity"
    assert Pillar.HARNESS.display == "Harness Engineering"


# --- Resolved tri-state -------------------------------------------------------


def test_resolved_singletons_are_identity_comparable() -> None:
    assert ABSENT is ABSENT
    assert UNKNOWN is UNKNOWN
    assert ABSENT is not UNKNOWN


def test_known_holds_value_and_is_distinct_from_sentinels() -> None:
    k = Known(30)
    assert k.value == 30
    assert k is not ABSENT and k is not UNKNOWN
    assert Known(30) == Known(30)


# --- fingerprint --------------------------------------------------------------


def test_normalize_anchor_collapses_whitespace() -> None:
    assert normalize_anchor("  a   b\n\tc ") == "a b c"


def test_fingerprint_is_deterministic_and_16_hex() -> None:
    fp = compute_fingerprint("PLB-RES-001", "a/b.py", "x = f()", 0)
    assert fp == compute_fingerprint("PLB-RES-001", "a/b.py", "x = f()", 0)
    assert len(fp) == 16
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_independent_of_line_number() -> None:
    # Same statement text at two different lines -> identical fingerprint key
    # (line is not part of the payload). Disambiguation is via ordinal only.
    a = compute_fingerprint("PLB-RES-001", "a.py", "client.create()", 0)
    b = compute_fingerprint("PLB-RES-001", "a.py", "client.create()", 0)
    assert a == b


def test_fingerprint_changes_with_anchor_text() -> None:
    a = compute_fingerprint("PLB-RES-001", "a.py", "client.create()", 0)
    b = compute_fingerprint("PLB-RES-001", "a.py", "client.fetch()", 0)
    assert a != b


def test_fingerprint_whitespace_insensitive() -> None:
    a = compute_fingerprint("PLB-RES-001", "a.py", "x   =    f()", 0)
    b = compute_fingerprint("PLB-RES-001", "a.py", "x = f()", 0)
    assert a == b


# --- assign_fingerprints ------------------------------------------------------


def test_identical_defects_get_distinct_stable_fingerprints() -> None:
    # Two identical statements in the same file -> distinct fingerprints by ordinal.
    drafts = [
        _draft("PLB-RES-001", "a.py", "client.create()", line=20),
        _draft("PLB-RES-001", "a.py", "client.create()", line=10),
    ]
    findings = assign_fingerprints(drafts)
    fps = {f.fingerprint for f in findings}
    assert len(fps) == 2  # distinct


def test_ordinal_assigned_by_line_order_not_input_order() -> None:
    # Input order is reversed; ordinal 0 must go to the earlier line deterministically.
    forward = assign_fingerprints(
        [_draft("PLB-RES-001", "a.py", "f()", 10), _draft("PLB-RES-001", "a.py", "f()", 20)]
    )
    reverse = assign_fingerprints(
        [_draft("PLB-RES-001", "a.py", "f()", 20), _draft("PLB-RES-001", "a.py", "f()", 10)]
    )
    by_line_forward = {f.line: f.fingerprint for f in forward}
    by_line_reverse = {f.line: f.fingerprint for f in reverse}
    assert by_line_forward == by_line_reverse  # input order does not affect result


def test_distinct_anchors_do_not_share_ordinal_space() -> None:
    findings = assign_fingerprints(
        [_draft("PLB-RES-001", "a.py", "f()", 10), _draft("PLB-RES-001", "a.py", "g()", 20)]
    )
    anchor_by_line = {10: "f()", 20: "g()"}
    # Each is the sole occurrence of its anchor -> both ordinal 0, distinct anchors.
    assert findings[0].fingerprint != findings[1].fingerprint
    for f in findings:
        expected = compute_fingerprint(f.rule_id, f.file, anchor_by_line[f.line], 0)
        assert f.fingerprint == expected


def test_finding_is_frozen() -> None:
    f = assign_fingerprints([_draft("PLB-RES-001", "a.py", "f()", 1)])[0]
    try:
        f.line = 99  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("Finding must be immutable")


# --- sort key -----------------------------------------------------------------


def test_finding_sort_key_orders_by_file_then_line() -> None:
    findings = assign_fingerprints(
        [
            _draft("PLB-RES-001", "b.py", "f()", 1),
            _draft("PLB-RES-001", "a.py", "f()", 50),
            _draft("PLB-RES-001", "a.py", "f()", 2),
        ]
    )
    ordered = sorted(findings, key=finding_sort_key)
    assert [(f.file, f.line) for f in ordered] == [("a.py", 2), ("a.py", 50), ("b.py", 1)]
