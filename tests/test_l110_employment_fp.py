"""L1.10 falso positivo employment — scoperto DALLA trust console (2026-07-10).

Il primo dato reale mostrato dalla UI era sbagliato: "Bob works at Acme
Corporation" (con verified_by!) finiva in quarantena perché L1.10 matcha
``\\bworks\\b`` ovunque — ma "PERSON works at/for ORG" è una collocazione
biografica, non un claim di funzionamento. È il fatto più comune in una
memoria personale/aziendale: quarantenarlo è un FP sistematico.

Discriminante precisa (precision-first): l'occorrenza è employment quando
"works/working" è seguito da " at|for " + parola Capitalizzata (nome
proprio). "the system works at scale" resta un claim ("scale" minuscolo);
"everything works fine" resta un claim (nessun at/for). Il caso
"works as a nurse" NON è coperto qui (FP noto, documentato): la rete dietro
è L1.20 semantico, il costo del miss keyword è basso.
"""
from __future__ import annotations

import pytest

from engram.client import Memory
from engram.l1_works_detector import detect_unsupported_works_claim


# ---- unit: il detector distingue i due sensi --------------------------------

@pytest.mark.parametrize("biographical", [
    "Bob works at Acme Corporation",
    "She works for Google",
    "Alice is working at Microsoft in the Berlin office",
    "Da marzo Bob works for Ferrari",  # code-switch reale import ChatGPT
])
def test_employment_use_is_not_a_functionality_claim(biographical):
    assert detect_unsupported_works_claim(
        proposition=biographical, verified_by=None) is None


@pytest.mark.parametrize("claim", [
    "the system works at scale",            # 'at' ma destinazione minuscola
    "everything works fine now",            # nessun at/for
    "the deployment works and is verified in production",
    "the integration works for our use case",  # 'for' + minuscolo
    "confirmed: migration succeeded",       # altri keyword intatti
])
def test_functionality_claims_still_detected(claim):
    assert detect_unsupported_works_claim(
        proposition=claim, verified_by=None) is not None


def test_runtime_evidence_still_clears_the_claim():
    assert detect_unsupported_works_claim(
        proposition="the system works at scale",
        verified_by=["pytest:test_scale_PASS"]) is None


# ---- integrazione: il fatto biografico entra ammesso -------------------------

def test_biographical_fact_with_evidence_is_admitted(tmp_path):
    m = Memory(tmp_path / "m.db")
    r = m.add("Bob works at Acme Corporation", topic="work",
              verified_by=["linkedin-profile"])
    assert r["status"] != "quarantined", (
        "employment + evidenza documentale NON è un claim di funzionamento")
    assert not any(w.get("layer") == "L1.10" for w in r.get("warnings", []))
