"""Il recall, coi segnali di default, ordina per una DICHIARAZIONE e non per la verifica.

Misurato sul corpus reale il 2026-08-17 (`verimem doctor`, HEAD c68a8254):

    fatti GIUDICATI dal moat        confidence = 0.5 su 5055 su 5155  (il default
                                    del modello: il moat non tocca questo campo)
    fatti MAI GIUDICATI             0.95 su 2275 · 1.00 su 300 · 0.85 su 2351
                                    (il valore che chi scrive si e' dichiarato)

Il verdetto del moat esiste e discrimina — `confidence_tier` vale `high` su 4728
giudicati e `low` su 356 — ma nessuna delle graduatorie di `rank_list_builders`
lo usa: ci sono `recency_rank`, `confidence_rank` (ORDER BY confidence DESC) e
`recency_decayed_rank`.

E `fuse_recall` accende `confidence` PER DEFAULT:

    fuse_recall.py:47  _DEFAULT_SIGNALS = frozenset({"recency", "confidence"})

`tests/test_fuse_recall.py` passa sempre `enabled_signals` esplicito, quindi il
comportamento di DEFAULT non e' asserito da nessuna parte: questo file lo asserisce,
e documenta la conseguenza.

Non c'e' un errore di calcolo da nessuna parte: `confidence_rank` fa esattamente
cio' che il suo nome dichiara ed e' testata. Il difetto e' che la scelta di
default usa il campo che chi e' sotto esame puo' scegliersi, e la graduatoria
sulla verifica non esiste.

-- ws1 Riscontro (firma commit: Curie)
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.fuse_recall import _DEFAULT_SIGNALS
from verimem.rank_list_builders import confidence_rank


def _store_minimo(path):
    """Due fatti: uno VERIFICATO dal moat, uno che si e' dichiarato certo."""
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, topic TEXT,"
        " confidence REAL, confidence_tier TEXT, grounding_score REAL,"
        " created_at REAL, superseded_by TEXT)"
    )
    con.executemany(
        "INSERT INTO facts VALUES (?,?,?,?,?,?,?,NULL)",
        [
            # giudicato dal moat: il moat NON scrive `confidence`, resta al default
            ("verificato", "il pacchetto pesa tre chilobyte", "t",
             0.5, "high", 99.9, 1000.0),
            # mai giudicato: chi ha scritto si e' dichiarato quasi certo
            ("autodichiarato", "il pacchetto pesa tre megabyte", "t",
             0.95, None, None, 1000.0),
        ],
    )
    con.commit()
    con.close()


def test_il_default_del_recall_include_la_confidenza(tmp_path):
    """Il default non e' asserito altrove: `test_fuse_recall` passa sempre i segnali."""
    assert "confidence" in _DEFAULT_SIGNALS, (
        "se questo cade, il default e' cambiato: rileggi il resto del file, "
        "perche' la conseguenza documentata qui sotto potrebbe non valere piu'"
    )
    assert not {"grounding_score", "confidence_tier", "verification"} & _DEFAULT_SIGNALS, (
        "un segnale sulla VERIFICA e' entrato nei default: e' la cura, "
        "e questo file va riscritto"
    )


@pytest.mark.xfail(
    strict=True,
    reason="difetto documentato: manca un `verification_rank`, quindi la sola "
           "graduatoria disponibile mette il fatto verificato DOPO quello che si "
           "e' dichiarato certo da solo (misurato sul corpus 17/08: 5055 giudicati "
           "a 0.5 contro 2275 mai giudicati a 0.95)",
)
def test_il_verificato_viene_prima_di_chi_si_e_dichiarato_certo(tmp_path):
    db = tmp_path / "semantic.db"
    _store_minimo(db)

    ordine = confidence_rank(db, limit=10, topic="t")

    assert ordine[0] == "verificato", (
        f"il recall mette per primo {ordine[0]!r}: ordina per `confidence`, "
        "che e' la dichiarazione di chi scrive, e non per `confidence_tier` "
        "o `grounding_score`, che sono il verdetto del moat"
    )
