"""The completion detector knew "firmato" and not "pagato".

Found by using the product on an invoicing case, 2026-07-29:

    claim   "Il totale della fattura e 1240 euro ed e gia stato PAGATO dal
             cliente"
    source  "Fattura 88: imponibile 1000, IVA 240, totale 1240 euro.
             Scadenza 30 giorni."
    moat    99.8  TRUSTED

The source does not say it was paid — "scadenza 30 giorni" says the opposite.
This is exactly the class the relation trigger exists to catch, and it stayed
silent because ``pagato`` was not in the hand-written list. Neither were paid,
saldato, rimborsato, refunded, approvato, approved. ``firmato`` was, so the
identical sentence about a signature DID escalate.

That is the same defect cured on the critic-orchestrator the night before:
a list that enumerates what someone happened to imagine. Adding "pagato" fixes
one word and leaves the class open.

A completed state has a SHAPE, in both languages the corpus uses: an auxiliary
plus a past participle — "è stato pagato", "has been paid", "was refunded". The
trigger stays what it was, an ASYMMETRY: the fact announces the completed
action and the source never names it. So the participle is extracted from the
fact and looked for in the source; a source that already says "pagato" asserts
the completion and nothing escalates.
"""
from __future__ import annotations

import pytest

from verimem.relation_claim import unverified_relation


@pytest.mark.parametrize("fact,source", [
    # the case that found this
    ("Il totale della fattura e 1240 euro ed e gia stato pagato dal cliente.",
     "Fattura 88: imponibile 1000, IVA 240, totale 1240 euro. Scadenza 30 giorni."),
    ("The invoice has been paid in full.",
     "Invoice 88: total 1240 euro, due in 30 days."),
    ("The order was refunded to the customer.",
     "The customer opened a refund request on Tuesday."),
    ("La pratica e stata approvata dal comitato.",
     "La pratica e stata inviata al comitato per la valutazione."),
    ("Il contratto e stato firmato dalle parti.",
     "Il contratto e stato inviato per la firma."),
    ("The patient was discharged on Monday.",
     "The patient was admitted on Friday and remains under observation."),
])
def test_a_completed_state_the_source_never_names_is_flagged(fact, source):
    assert unverified_relation(source, fact) == "completion", (
        f"missed: {fact!r}"
    )


@pytest.mark.parametrize("fact,source", [
    ("Il totale e stato pagato dal cliente.",
     "Ricevuta: il totale e stato pagato dal cliente il 3 marzo."),
    ("The invoice has been paid.",
     "Bank statement: the invoice was paid on 3 March."),
    ("La pratica e stata approvata.",
     "Verbale: la pratica e stata approvata all'unanimita."),
])
def test_a_completion_the_source_does_assert_stays_silent(fact, source):
    """The asymmetry is the whole trigger. A source that names the same
    completed action asserts nothing new, and escalating it would spend a judge
    call on every faithful restatement."""
    assert unverified_relation(source, fact) is None, (
        f"false positive on a faithful restatement: {fact!r}"
    )


@pytest.mark.parametrize("text", [
    "Two people familiar with the matter said the plant is likely to close.",
    "Article 12 applies to listed companies with more than 500 employees.",
    "In the trial the treatment was effective in adults aged 18 to 65.",
    "The parcel is out for delivery from the local depot.",
    "The share price fell 8% on Tuesday.",
    "Il paziente e in osservazione dal lunedi.",
])
def test_the_controls_from_2026_07_28_still_do_not_escalate(text):
    """Unchanged: fact and source say the same thing."""
    assert unverified_relation(text, text) is None
