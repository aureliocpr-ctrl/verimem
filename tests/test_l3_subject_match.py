"""Subject matcher for the L3-semantic NLI pre-filter (P2, design GLM 2026-07-21).

The local NLI judge over-flags contradictions on pairs about DIFFERENT subjects
(measured: the cosine 0.7 pre-filter is inert — 595/595 corpus pairs clear it).
The cure is a subject pre-filter: only pairs ABOUT the same subject reach the
NLI. Rule (head-noun + modifier agreement, NOT token overlap):

  same head noun AND (modifiers overlap OR one side's modifiers are a subset
  OR either side has no modifier)  ->  COMPARE (True);  else SKIP (False).
  Empty/pronoun subject -> wildcard COMPARE (fail-open: never silently skip a
  real conflict we cannot attribute).

Pure function in verimem.subject_extract; the gate wiring is separate and
env-gated default-off (ENGRAM_L3_SUBJECT_FILTER).
"""
from __future__ import annotations

import pytest

pytest.importorskip("verimem.subject_extract")
from verimem.subject_extract import same_subject  # noqa: E402

# true conflict about the SAME subject — MUST be compared (G4 keeps A>=8/8)
SAME = [
    ("The Rossi SpA contract expires on 31 January 2027.",
     "The Rossi SpA contract expires in 2025."),
    # bare head on one side -> assume same (the conflict must still be judged)
    ("The contract expires in 2025.",
     "The Rossi SpA contract expires on 31 January 2027."),
    # modifiers overlap
    ("The payments team migrated to Stripe in 2025.",
     "The payments team still runs on the legacy processor."),
    # cross-entity: 'Tom's startup' and 'Tom' are the same subject sphere — a
    # REAL bench-A conflict (acquired vs runs independently) the plain head-noun
    # rule skipped (predicted limitation, P2 design 2026-07-21). Heads differ but
    # one side's head appears in the other side's subject tokens -> compare.
    ("Tom's startup was acquired by Google.",
     "Tom still runs his startup independently."),
]

# different-subject pairs the NLI wrongly flagged (case F*) — MUST be skipped
DIFFERENT = [
    ("The arbitration clause was added in the 2024 amendment.",
     "The settlement resolved all outstanding claims between the parties."),
    ("The arbitration clause was added in the 2024 amendment.",
     "The easement is documented in the 1998 deed at the land registry."),
    ("Q3 revenue was 1.2 million euros.",
     "The invoice total is 12,450 euros."),
    # shared head noun, disjoint modifiers -> different subject
    ("The payments team migrated to Stripe in 2025.",
     "The design team runs a weekly critique on Fridays."),
    ("The Rossi SpA contract expires on 31 January 2027.",
     "The vendor contract auto-renews unless cancelled 60 days prior."),
]

# unattributable subject -> wildcard compare (fail-open, the SAFE direction)
WILDCARD = [
    ("It was completed on Tuesday.", "The audit was completed on Friday."),
    ("", "The audit was completed on Friday."),
]


@pytest.mark.parametrize("a,b", SAME)
def test_same_subject_pairs_are_compared(a, b):
    assert same_subject(a, b) is True


@pytest.mark.parametrize("a,b", DIFFERENT)
def test_different_subject_pairs_are_skipped(a, b):
    assert same_subject(a, b) is False


@pytest.mark.parametrize("a,b", WILDCARD)
def test_unattributable_subject_fails_open_to_compare(a, b):
    assert same_subject(a, b) is True
    assert same_subject(b, a) is True


def test_symmetric():
    a, b = DIFFERENT[0]
    assert same_subject(a, b) == same_subject(b, a)
