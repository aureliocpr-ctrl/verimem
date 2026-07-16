"""L1 dev-claim detectors vs third-person biographies (FLAGS-AUDIT §8 item 4).

Measured on 300 HaluMem clean personal facts (probe 2026-07-16, validate="fast"
defaults): 8/300 = 2.7% false positives, all downgrades of legitimate memories:

  * 6× L1.7  — the task-state phrase list was matched as BARE SUBSTRINGS, so
               "is open" fired inside "hi[s open]ness" and on the personal
               idiom "is open to exploring" (availability, not task state);
  * 1× L1.10 — "works in the healthcare industry" (occupation; the detector's
               own comment documented "works as a nurse" as a known FP debt);
  * 1× L1.12 — "secured interviews and job offers" ('secured' = obtained,
               not a security-hardening claim).

Contract pinned here: the 8 REAL measured FPs persist clean, while the true
dev-claims each detector exists for keep firing (no recall loss on the moat).
"""
from __future__ import annotations

import pytest

from engram.anti_confab_gate import run_validation_gate


def _gate(prop: str):
    return run_validation_gate(proposition=prop, verified_by=None,
                               topic="personal/bio", agent=None,
                               validate="fast")


# The 8 exact false positives measured on HaluMem (probe 2026-07-16).
_MEASURED_FPS = [
    "Martin Mark works in the healthcare industry",
    "Martin secured interviews and job offers through his expanding "
    "social network.",
    "Martin is open to exploring non-violent action games to enhance "
    "cognitive functions, aligning with his values of peace and well-being.",
    "Martin's evolving game preferences reflect his openness to new "
    "experiences and personal growth.",
    "Martin's evolving beverage preferences reflect his openness to new "
    "experiences and personal growth, including exploring coffee for "
    "relaxation.",
    "Martin's music preference has evolved to include heavy metal for its "
    "therapeutic potential, reflecting his openness to new experiences.",
    "Martin's enthusiasm for exploring different music genres is evident "
    "in his openness to new experiences, aiming to integrate them into "
    "his routine.",
    "Martin's creative motivation is reflected in his openness to explore "
    "new interests like iguanas.",
]


@pytest.mark.parametrize("prop", _MEASURED_FPS)
def test_measured_biography_fps_persist_clean(prop):
    r = _gate(prop)
    assert r.action == "persist", (
        f"legitimate personal fact downgraded: {[w.get('layer') for w in r.warnings]}"
        f" — {prop[:60]!r}")


# ---- no-recall-loss guards: the TRUE claims each detector exists for --------

@pytest.mark.parametrize("prop", [
    "The PR is open",                       # word-boundary match must survive
    "The migration task is still pending",
    "Il ticket è ancora aperto",
])
def test_true_task_state_claims_still_fire(prop):
    r = _gate(prop)
    assert any(w.get("layer") == "L1.7" for w in r.warnings), (
        f"L1.7 lost a true task-state claim: {prop!r}")


@pytest.mark.parametrize("prop", [
    "The fix works",
    "The parser works as expected now",     # 'as' + participle ≠ occupation
    "The new module works in production",   # 'in' + non-industry ≠ occupation
])
def test_true_works_claims_still_fire(prop):
    r = _gate(prop)
    assert any(w.get("layer") == "L1.10" for w in r.warnings), (
        f"L1.10 lost a true works claim: {prop!r}")


@pytest.mark.parametrize("prop", [
    "The endpoint is secured",
    "We secured the database against injection",
])
def test_true_security_claims_still_fire(prop):
    r = _gate(prop)
    assert any(w.get("layer") == "L1.12" for w in r.warnings), (
        f"L1.12 lost a true security claim: {prop!r}")


def test_existing_employment_exclusion_unbroken():
    # the already-shipped capitalized-org exclusion ("works at Acme") stays
    r = _gate("Sofia works at Deloitte in Milan")
    assert not any(w.get("layer") == "L1.10" for w in r.warnings)
