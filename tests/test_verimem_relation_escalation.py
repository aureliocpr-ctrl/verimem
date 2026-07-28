"""The CE is confident exactly where it is blind, so the band never catches it.

Escalation to a reasoning judge fires for CE scores inside [threshold, tau_hi) —
the sliver the CE reports itself unsure about. Measured 2026-07-28 on eleven
domain deformations, the CE got 8 right and its three misses scored 88, 100 and
100: far ABOVE the band. The safety net is hung under the cases it never drops.

The three misses are one class — relations between facts, not words in them:

    modality   "prevents" from "associated with a small reduction"      100
    state      "was delivered" from "out for delivery from the depot"    88
    causation  "fell BECAUSE the CEO resigned" from a source that
               reports the fall and the resignation separately          100

A similarity model cannot see these: every word of the source is present, only
the relation is invented. But the relation is announced LEXICALLY, and — the
part that keeps this from becoming noise — it is announced in the FACT while
being absent from the SOURCE. A causal claim whose source is equally causal
asserts nothing new and must not escalate.

So the trigger is an ASYMMETRY, not a keyword. And escalating costs one judge
call, never a block, so a false positive here is cheap and a false negative is
what the product exists to prevent.
"""
from __future__ import annotations

import pytest

from verimem.relation_claim import unverified_relation


@pytest.mark.parametrize("fact,source,kind", [
    ("The share price fell because of the CEO resignation.",
     "The share price fell 8% on Tuesday. The CEO resigned the same week.",
     "causal"),
    ("The shipment was delivered to the customer.",
     "Carrier scan: parcel arrived at the local depot and is out for delivery.",
     "completion"),
    ("Vitamin D prevents respiratory infections.",
     "The meta-analysis found vitamin D supplementation was associated with a "
     "small reduction in respiratory infections.",
     "modality"),
    ("Revenue grew 45% year over year.",
     "Revenue of 4.2bn, up from 3.75bn last year.",
     "derived-quantity"),
])
def test_a_relation_the_source_does_not_assert_is_flagged(fact, source, kind):
    got = unverified_relation(source, fact)
    assert got == kind, f"expected {kind}, got {got!r}"


@pytest.mark.parametrize("text", [
    "Two people familiar with the matter said the plant is likely to close.",
    "Article 12 applies to listed companies with more than 500 employees.",
    "In the trial the treatment was effective in adults aged 18 to 65.",
    "The parcel is out for delivery from the local depot.",
    "The share price fell 8% on Tuesday.",
])
def test_a_faithful_restatement_never_escalates(text):
    """The controls: fact and source say the same thing. Escalating these would
    make the trigger fire on most writes and turn into noise."""
    assert unverified_relation(text, text) is None


def test_a_relation_already_in_the_source_is_not_new():
    """The asymmetry is the point: same relation on both sides asserts nothing
    the source did not."""
    assert unverified_relation(
        "The outage was caused by a failed migration.",
        "Post-mortem: the outage was caused by a failed migration.") is None
    assert unverified_relation(
        "Revenue grew 12% year over year.",
        "Revenue grew 12% year over year according to the filing.") is None


def test_empty_or_missing_input_is_not_a_relation():
    assert unverified_relation("", "") is None
    assert unverified_relation(None, None) is None
    assert unverified_relation("some source", "") is None
