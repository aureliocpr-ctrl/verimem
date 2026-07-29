"""When the gate can SEE the evidence it is asking for, it should say so.

An L1 detector quarantines "Wave 72 skills_recent done, last commit ff2aaa3e"
and answers "no closing criteria evidence in verified_by. Add at least one of:
task:<id>_closed, pytest:<t>_PASS, pr:<n>_merged...". The commit is right there
in the sentence the gate just parsed.

Measured on the live corpus 2026-07-28: 174 of 509 quarantined facts (34.2%)
name a commit, a file:line, a test result or a PR in their own prose — 95, 30,
69 and 18 respectively.

The verdict must NOT change: a SHA inside prose is an assertion, while the same
SHA in verified_by is checkable and provenance_validator actually checks it with
git rev-parse. Reading evidence out of the sentence would let a writer clear the
gate by describing proof it never had. What changes is that the rejection
becomes actionable instead of generic.
"""
from __future__ import annotations

import pytest

from verimem.evidence_hint import evidence_in_text, hint_for


@pytest.mark.parametrize("text,kind,value", [
    ("HippoAgent @ 2026-05-11: 107 tools, last commit ff2aaa3e. Wave 72 done.",
     "commit", "ff2aaa3e"),
    ("GroundProbe v0.3.0 stable 2026-05-15 commit e0c9e48: profiler.",
     "commit", "e0c9e48"),
    ("Fixed the parser, see verimem/composer.py:87 for the guard.",
     "file", "verimem/composer.py:87"),
    ("The suite is green: pytest tests/ EXIT=0 after the change.",
     "test", "pytest"),
    ("Landed in PR #196 after review.", "pr", "PR #196"),
])
def test_a_reference_in_the_prose_is_recognised(text, kind, value):
    found = dict(evidence_in_text(text))
    assert kind in found, f"{kind} not found in {found}"
    assert value.lower() in found[kind].lower()


def test_prose_with_no_reference_produces_no_hint():
    assert hint_for("The migration is done and everything works perfectly.") is None
    assert hint_for("") is None
    assert hint_for(None) is None


def test_the_hint_names_what_was_cited_and_where_to_put_it():
    h = hint_for("Wave 72 skills_recent done, last commit ff2aaa3e.")
    assert h and "ff2aaa3e" in h
    assert "verified_by" in h


def test_the_hint_does_not_propose_a_form_of_its_own():
    """Measured over 60 quarantined facts carrying a SHA: commit:<sha> unblocks
    6, pytest:<t>_PASS unblocks 40, both together 47. A completion claim needs a
    closing criterion and a commit is not one, so a hint that names commit:
    because it saw a SHA points at the path that works one time in ten. The
    detector already lists the forms it accepts; the hint points there."""
    h = hint_for("Wave 72 skills_recent done, last commit ff2aaa3e.")
    assert "commit:ff2aaa3e" not in h, h
    assert "listed above" in h, h


def test_the_hint_says_why_prose_is_not_evidence():
    """The distinction is the whole reason the verdict does not change."""
    h = hint_for("Closed it, see commit ff2aaa3e.")
    assert h and "assertion" in h.lower()
