"""«Quanti fatti serviti hanno un verdetto» era una media fra due mondi.

Il quartetto porta `judged` da ieri sera, ed è un numero che ho citato
tutta la notte: «4271 fatti serviti su 5633 senza un verdetto, il 75,8%».
Oggi ws1 ha misurato che **`clp save` non chiama il gate** — INSERT SQL
diretto con `status` fisso a `user_manual` — e ws5 ha corretto un proprio
numero per la stessa ragione, chiamandola «la trappola del denominatore».

Il mio `judged` ce l'ha dentro. Sul corpus reale, per status:

    model_claim        3074 servibili · 1800 con verdetto · 58.6%
    user_manual        2493 servibili ·    0 con verdetto ·  0.0%
    provisional         343 · 0     legacy_unverified 115 · 0
    bootstrap_rule       24 · 0     bootstrap_lesson   14 · 0

⇒ La popolazione che passa dal gate è giudicata al **58,6%**; quella che
non ci passa non lo è mai, per costruzione. Un aggregato che le somma
descrive una media che non corrisponde a nessuna delle due, e fa sembrare
il gate peggiore di com'è.

⚠️ NON invento l'etichetta «mai passato dal gate»: quale status venga da
quale porta lo sa chi possiede il write path, e `user_manual` è
l'osservabile, non la causa. Espongo la RIPARTIZIONE per status e dichiaro
che l'aggregato è una mescolanza — chi conosce le porte può leggerla.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.client import Memory
from verimem.retirement_log import survivability_counts


@pytest.fixture()
def mem(tmp_path):
    m = Memory(tmp_path / "m.db")
    a = m.add("the depot holds 10 crates", topic="log/a")["id"]
    b = m.add("the yard holds 5 pallets", topic="log/b")["id"]
    with sqlite3.connect(m.semantic.db_path) as con:
        # uno giudicato, e uno scritto da una porta che il gate non tocca
        con.execute("UPDATE facts SET grounding_score = 97.0 WHERE id = ?", (a,))
        con.execute("UPDATE facts SET status = 'user_manual' WHERE id = ?", (b,))
    return m


def test_il_quartetto_ripartisce_i_giudicati_per_STATUS(mem):
    q = survivability_counts(mem.semantic)
    per_status = {v["status"]: v for v in q["judged_by_status"]}

    assert per_status["model_claim"]["judged"] == 1
    assert per_status["user_manual"]["judged"] == 0
    assert per_status["user_manual"]["servable"] == 1


def test_l_aggregato_RESTA_e_dichiara_di_essere_una_mescolanza(mem):
    """Non tolgo il numero: tolgo l'illusione che descriva una cosa sola.
    Chi lo cita deve sapere che somma popolazioni con regole diverse."""
    q = survivability_counts(mem.semantic)
    assert q["judged"] == 1
    assert "mixes" in q["formula"].lower() or "mixture" in q["formula"].lower()
    assert "status" in q["formula"].lower()


def test_le_righe_sono_ordinate_per_grandezza(mem):
    """Chi guarda vuole vedere subito la popolazione che pesa: sul corpus
    reale sono `model_claim` 3074 e `user_manual` 2493."""
    q = survivability_counts(mem.semantic)
    conteggi = [v["servable"] for v in q["judged_by_status"]]
    assert conteggi == sorted(conteggi, reverse=True), q["judged_by_status"]


def test_NON_inventa_l_etichetta_mai_passato_dal_gate(mem):
    """`user_manual` è un OSSERVABILE; «non è passato dal gate» è una
    causa che sa chi possiede il write path. La stessa distinzione che ho
    già sbagliato oggi con la parola «housekeeping»."""
    q = survivability_counts(mem.semantic)
    testo = (q["formula"] + str(q["judged_by_status"])).lower()
    for parola in ("never_gated", "bypassed", "ungated"):
        assert parola not in testo, (parola, testo[:200])


def test_un_corpus_di_un_solo_status_non_cambia_il_totale(mem, tmp_path):
    """Guardia sull'aritmetica: la ripartizione deve sommare al numero che
    il quartetto dichiara, o si legge come se mancasse qualcosa."""
    q = survivability_counts(mem.semantic)
    assert sum(v["servable"] for v in q["judged_by_status"]) == q["servable"]
    assert sum(v["judged"] for v in q["judged_by_status"]) == q["judged"]
