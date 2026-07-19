"""Unit tests for the shared numeric-conflict primitives.

These are the single source of truth used by BOTH validate_claim (write-
time) and facts_conflict.find_numeric_conflicts (batch scan), so they are
tested here once, directly.
"""
from __future__ import annotations

from verimem.quantity_match import (
    extract_quantities,
    norm_unit,
    numeric_conflict,
)

# ---------- norm_unit / extract_quantities ------------------------------


def test_norm_unit_synonyms_and_plurals() -> None:
    assert norm_unit("milliseconds") == "ms"
    assert norm_unit("ms") == "ms"
    assert norm_unit("minutes") == "min"
    assert norm_unit("entries") == "entry"
    assert norm_unit("requests") == "request"
    assert norm_unit("snapshots") == "snapshot"


def test_extract_quantities_excludes_bare_years() -> None:
    # 2024 with no unit is a YEAR, not a quantity.
    assert extract_quantities("released in 2024") == set()
    # but a year-shaped number WITH a unit is a quantity.
    assert ("request", 2024.0) in extract_quantities("2024 requests per day")


def test_extract_quantities_unit_normalised() -> None:
    assert ("min", 30.0) in extract_quantities("a TTL of 30 minutes")
    assert ("ms", 200.0) in extract_quantities("backoff at 200ms")
    assert ("entry", 1024.0) in extract_quantities("bounded at 1024 entries")


def test_extract_quantities_ignores_identifier_digits() -> None:
    """Digits EMBEDDED in commit SHAs / versions / loop ids are NOT
    quantities. (Empirically critical: without this a live-corpus scan
    produced ~700k false conflicts from SHA/id digits like 'a64d252'.)"""
    assert extract_quantities("commit a64d252 shipped the gate") == set()
    assert extract_quantities("bumped to v38 of the schema") == set()
    assert extract_quantities("LOOP178 closed the bridge") == set()
    # …but a clean standalone quantity in the same kind of sentence is kept.
    assert ("min", 30.0) in extract_quantities("commit a64d252 set TTL to 30 minutes")


def test_extract_quantities_following_function_word_is_not_a_unit() -> None:
    # "30 and 45" → two bare numbers, NOT a quantity with unit 'and'.
    q = extract_quantities("we shipped 30 and improved 45 things")
    assert ("and", 30.0) not in q
    assert all(u != "and" for (u, _v) in q)


# ---------- numeric_conflict --------------------------------------------


def test_conflict_same_unit_different_value_same_subject() -> None:
    c = numeric_conflict(
        "Sessions expire after 45 minutes of inactivity.",
        "Sessions are stored with a TTL of 30 minutes.",
    )
    assert c is not None
    unit, va, vb = c
    assert unit == "min"
    assert {va, vb} == {45.0, 30.0}


def test_no_conflict_same_value() -> None:
    assert numeric_conflict(
        "Sessions expire after 30 minutes.",
        "Sessions have a TTL of 30 minutes.",
    ) is None


def test_no_conflict_unrelated_subject_same_unit() -> None:
    # Both use the unit 'entry' with different values, but the subjects
    # (ring buffer vs cache) share no distinctive word → not a conflict.
    assert numeric_conflict(
        "The ring buffer holds 256 entries.",
        "The cache is bounded at 1024 entries.",
    ) is None


def test_no_conflict_contrasting_qualifier() -> None:
    # read vs write timeout = different attribute, not a contradiction.
    assert numeric_conflict(
        "The read timeout is 30 seconds.",
        "The write timeout is 10 seconds.",
    ) is None


def test_no_conflict_when_no_quantity() -> None:
    assert numeric_conflict(
        "Sessions are keyed by a UUID.",
        "Sessions are stored in a table.",
    ) is None


def test_conflict_is_directional_but_symmetric_on_presence() -> None:
    a = "The cache holds at most 4096 entries."
    b = "The cache is bounded at 1024 entries."
    assert numeric_conflict(a, b) is not None
    assert numeric_conflict(b, a) is not None


# ---------- lexical expansion 0.7.0: version / date / negation -----------
# Mandate 2026-07-19: the DEFAULT moat claim "numeric/version/date/negation"
# must be TRUE. These primitives extend the same precision-first, zero-LLM
# design: same-subject guard, deterministic extraction, disjoint => conflict.

from verimem.quantity_match import (  # noqa: E402
    date_conflict,
    extract_dates,
    extract_versions,
    negation_conflict,
    version_conflict,
)


def test_extract_versions_dotted_and_v_prefixed() -> None:
    assert extract_versions("Orion ships on version 2.3.1.") == {"2.3.1"}
    assert extract_versions("upgraded to v4.0.0 yesterday") == {"4.0.0"}
    # two-component only with a version keyword nearby (else it's a decimal)
    assert extract_versions("Orion ships on version 2.3.") == {"2.3"}
    assert extract_versions("the reactor operates at 2.3 degrees") == set()


def test_version_conflict_same_subject_different_version() -> None:
    got = version_conflict(
        "Orion ships on version 2.3.1.",
        "Orion ships on version 4.0.0.",
    )
    assert got == ("2.3.1", "4.0.0") or got == ("4.0.0", "2.3.1")


def test_version_no_conflict_unrelated_subject() -> None:
    assert version_conflict(
        "Orion ships on version 2.3.1.",
        "Zephyr ships on version 4.0.0.",
    ) is None


def test_version_no_conflict_same_version() -> None:
    assert version_conflict(
        "Orion ships on version 2.3.1.",
        "Orion is still on version 2.3.1 today.",
    ) is None


def test_extract_dates_iso_and_month_names() -> None:
    assert extract_dates("The audit is on 2025-03-06.") == {(2025, 3, 6)}
    assert extract_dates("Project Aurora launches in March 2025.") == {(2025, 3, None)}
    assert extract_dates("the meeting moved to September") == {(None, 9, None)}


def test_date_conflict_same_year_different_month() -> None:
    got = date_conflict(
        "Project Aurora launches in March 2025.",
        "Project Aurora launches in September 2025.",
    )
    assert got is not None


def test_date_conflict_iso_same_year_different_day() -> None:
    got = date_conflict(
        "The compliance audit is on 2025-03-06.",
        "The compliance audit is on 2025-09-20.",
    )
    assert got is not None


def test_date_no_conflict_different_years_left_to_year_rule() -> None:
    # different YEARS are the existing year-disjoint rule's job — the date
    # detector must not double-handle them.
    assert date_conflict(
        "Project Aurora launches in March 2024.",
        "Project Aurora launches in March 2025.",
    ) is None


def test_date_no_conflict_unrelated_subject() -> None:
    assert date_conflict(
        "Project Aurora launches in March 2025.",
        "The Beta review happens in September 2025.",
    ) is None


def test_negation_conflict_polarity_flip_same_statement() -> None:
    assert negation_conflict(
        "The vendor contract is signed.",
        "The vendor contract is not signed.",
    ) is not None


def test_negation_conflict_never_variant() -> None:
    assert negation_conflict(
        "The endpoint is reachable from the DMZ.",
        "The endpoint is never reachable from the DMZ.",
    ) is not None


def test_negation_no_conflict_same_polarity() -> None:
    assert negation_conflict(
        "The vendor contract is signed.",
        "The vendor contract is signed and archived.",
    ) is None


def test_negation_no_conflict_different_subject() -> None:
    # negator on an UNRELATED statement must not flag: different subject.
    assert negation_conflict(
        "The vendor contract is signed.",
        "The supplier invoice is not paid.",
    ) is None
