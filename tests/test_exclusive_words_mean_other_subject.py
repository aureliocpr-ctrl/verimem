"""Attributi contrapposti in ITALIANO — e un'euristica falsificata.

La batteria di ampiezza (tests/test_everyday_memory_survives.py) ha trovato il
25/07 che "il gate legge in 45 ms" ritirava "il gate scrive in 300 ms":
CONTRAST_QUALIFIERS conteneva {read, write} in INGLESE e questo store e' scritto
in italiano.

STORIA DELL'ERRORE, perche' non si ripeta. Il primo tentativo fu un criterio
STRUTTURALE — "ciascun lato ha esattamente una parola distintiva che l'altro non
ha, quindi sono soggetti o attributi diversi" — che sembrava elegante e generale.
E' stato FALSIFICATO da due test che esistevano gia':

    "The cache holds at most 4096 entries." / "The cache is bounded at 1024"
        -> esclusivi {hold}/{bounded}: SINONIMI, il conflitto e' vero
    "Alice lives in Rome" / "Alice lives in Paris"
        -> esclusivi {rome}/{paris}: il VALORE e' cambiato, il supersede e' giusto

Un attributo opposto, un sinonimo e un valore cambiato hanno la stessa forma
lessicale: la differenza e' semantica e nessun conteggio di token la vede. Qui la
LISTA e' il design corretto, perche' le coppie contrapposte sono un insieme
piccolo e conosciuto — al contrario dei kind di indice, dove la lista chiusa era
sbagliata e serviva la posizione.
"""
from __future__ import annotations

from verimem.quantity_match import numeric_conflict


def test_italian_opposed_attributes_do_not_conflict():
    assert numeric_conflict("il gate legge in 45 ms",
                            "il gate scrive in 300 ms") is None
    assert numeric_conflict("la coda in ingresso tiene 100 messaggi",
                            "la coda in uscita tiene 500 messaggi") is None
    assert numeric_conflict("la latenza minima e 12 ms",
                            "la latenza massima e 900 ms") is None
    assert numeric_conflict("il path caldo risponde in 45 ms",
                            "il path freddo risponde in 4900 ms") is None


def test_english_pairs_do_not_regress():
    assert numeric_conflict("the read timeout is 30 seconds",
                            "the write timeout is 90 seconds") is None
    assert numeric_conflict("the staging cluster has 3 nodes",
                            "the production cluster has 30 nodes") is None


def test_the_falsified_heuristic_stays_out():
    """I due casi che hanno demolito il criterio strutturale: devono restare
    conflitti. Se qualcuno reintroduce quel criterio, questi cadono."""
    assert numeric_conflict("The cache holds at most 4096 entries.",
                            "The cache is bounded at 1024 entries.") is not None
    assert numeric_conflict("Sessions are stored with a TTL of 30 minutes.",
                            "Sessions expire after 45 minutes of inactivity.") is not None
