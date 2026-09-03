"""Audit#2 2026-06-08 A-6: consolidation._persist_master committed the master
Episode (mem.store) BEFORE the unique-index-guarded master Fact (sm.store). On a
cross-process consolidation race the loser's sm.store(f) raises IntegrityError
(caught upstream) but the Episode is already committed -> orphan episode with no
referencing master fact, accumulating under parallel auto-consolidate. Fix:
store the guarded Fact FIRST so a lost race aborts before any Episode is written
(f references ep.id, a soft cross-DB id, so fact-first is safe).
"""
from __future__ import annotations

import contextlib
import sqlite3

import pytest

from verimem import consolidation


class _FakeMem:
    def __init__(self):
        self.stored = []

    def store(self, ep):
        self.stored.append(ep)


class _FakeSmConflict:
    """Simulates losing the unique-index race on the master fact.

    ⚠️ ESPONE ANCHE ``_connect``, e non per completezza: dal 2026-09-02
    (``2f6655b6``, «la confidenza di un nodo consolidato si eredita invece di
    essere dichiarata») ``_persist_master`` legge le ``confidence`` dei fatti
    del cluster PRIMA dello ``store`` che deve abortire. Un doppio che espone
    il solo ``store`` fa morire il test con ``AttributeError: no attribute
    '_connect'`` — e un ``AttributeError`` non dice niente su cio' che il test
    presidia: il rosso sembra il difetto tornato, ed e' invece il doppio
    rimasto indietro.

    📌 La cura del 02/09 era giusta e il suo RED→GREEN era stato falsificato:
    quello che un RED→GREEN sulla propria cura NON vede sono i test-double
    ALTRUI che la nuova dipendenza rompe. Un doppio non e' tipizzato e tace
    finche' non lo si esegue.
    """

    def __init__(self):
        #: le scritture tentate: servono al controllo positivo sotto.
        self.tentativi = []
        self._db = sqlite3.connect(":memory:")
        self._db.row_factory = sqlite3.Row
        self._db.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, confidence REAL)")
        self._db.executemany("INSERT INTO facts VALUES (?, ?)",
                             [("a", 0.5), ("b", 0.4)])
        self._db.commit()

    @contextlib.contextmanager
    def _connect(self):
        yield self._db

    def store(self, f):
        self.tentativi.append(f)
        raise sqlite3.IntegrityError("UNIQUE constraint failed: idx_facts_auto_master_unique")


def test_persist_master_no_orphan_episode_on_fact_conflict():
    mem = _FakeMem()
    sm = _FakeSmConflict()
    cluster = {"topic": "proj/x", "topic_prefix": "proj/x",
               "fact_count": 2, "fact_ids": ["a", "b"]}
    master = {"topic": "proj/x", "proposition": "the consolidated master claim"}
    with pytest.raises(sqlite3.IntegrityError):
        consolidation._persist_master(sm, mem, cluster, master)
    # 🔑 CONTROLLO POSITIVO, che prima non c'era: senza, un giorno in cui la
    # funzione abortisse PRIMA di arrivare allo `store` (per un'eccezione di
    # tutt'altra natura, com'e' appena successo con `_connect`) questo test
    # resterebbe VERDE dichiarando un presidio che non ha piu' esercitato.
    assert sm.tentativi, (
        "il test deve arrivare fino allo `store` del fatto: se abortisce prima, "
        "l'assert sull'episodio orfano non prova nulla")
    assert mem.stored == [], "orphan episode committed before the fact conflict aborted"
