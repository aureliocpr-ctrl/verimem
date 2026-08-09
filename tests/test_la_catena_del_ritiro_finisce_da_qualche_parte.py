"""«Ritirato in favore di X» si legge come «l'informazione vive in X».

ws4, 2026-08-07: il 65% dei ritirati ha un sostituto **non servibile**, e
`superseded_by` è una catena che può finire nel nulla. Verificato qui
seguendo la catena fino in fondo sul corpus reale:

    1805 ritiri · la catena finisce su un fatto SERVIBILE  673 (37.3%)
                  finisce su un fatto non servibile       1131
                  punta inesistente                          1
                  cicli 0 · profondità max 13 · media 1.11

⚠️ E qui la disciplina che oggi mi ha già salvato due volte: **separando
per motivo il titolo si ribalta.**

    same-source evolution              107 · catena viva 107 (100.0%)
    heal_contradictions: numeric        21 · catena viva  21 (100.0%)
    exact-text dedup                   202 · catena viva 133 ( 65.8%)
    autohook-snapshot daily collapse  1463 · catena viva 406 ( 27.8%)

⇒ **Il write path ordinario non lascia MAI una catena morta.** Il 62.7%
che muore è quasi tutto la manutenzione del 2 luglio. L'aggregato da solo
accusava il prodotto di una cosa che non fa.

Perciò l'aggregato e lo split viaggiano INSIEME: un numero che si ribalta
quando lo dividi non va consegnato da solo.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_breakdown, retirement_log


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "m.db")


def _f(m: Memory, testo: str, topic: str) -> str:
    return m.add(testo, topic=topic)["id"]


def test_una_riga_dice_se_il_VINCITORE_e_ancora_servibile(mem):
    """«Ritirato in favore di X» dove X e' a sua volta ritirato non e' la
    stessa cosa, e la riga non lo diceva."""
    a = _f(mem, "the depot holds 10 crates", "log/a")
    b = _f(mem, "the depot holds 20 crates", "log/b")
    c = _f(mem, "the depot holds 30 crates", "log/c")
    mem.semantic.supersede(a, b, principal="t", reason="uno")
    mem.semantic.supersede(b, c, principal="t", reason="due")

    righe = {r["loser_id"]: r for r in retirement_log(mem.semantic)}
    assert righe[a]["winner_servable"] is False, righe[a]
    assert righe[b]["winner_servable"] is True, righe[b]


def test_un_vincitore_che_NON_ESISTE_si_dichiara(mem):
    """Sul corpus reale ce n'e' uno: `superseded_by` punta a un id che non
    c'e'. La riga usciva coi campi del vincitore tutti nulli e nessuno
    diceva che l'id non si risolve."""
    a = _f(mem, "the depot holds 10 crates", "log/a")
    b = _f(mem, "the depot holds 20 crates", "log/b")
    mem.semantic.supersede(a, b, principal="t", reason="uno")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("UPDATE facts SET superseded_by = 'ffffffffffff' "
                    "WHERE id = ?", (a,))

    r = next(x for x in retirement_log(mem.semantic) if x["loser_id"] == a)
    assert r["winner_missing"] is True, r
    assert r["winner_servable"] is None, "assente non e' 'non servibile'"


def test_il_riassunto_segue_la_CATENA_fino_in_fondo(mem):
    """Il sostituto immediato morto non vuol dire informazione persa: la
    catena puo' proseguire. E' la domanda che conta davvero."""
    a = _f(mem, "the depot holds 10 crates", "log/a")
    b = _f(mem, "the depot holds 20 crates", "log/b")
    c = _f(mem, "the depot holds 30 crates", "log/c")
    mem.semantic.supersede(a, b, principal="t", reason="uno")
    mem.semantic.supersede(b, c, principal="t", reason="uno")

    ch = retirement_breakdown(mem.semantic)["chain"]
    assert ch["ends_servable"] == 2, ch
    assert ch["ends_dead"] == 0
    assert ch["max_depth"] >= 2


def test_una_catena_che_muore_si_conta_come_morta(mem):
    a = _f(mem, "the depot holds 10 crates", "log/a")
    b = _f(mem, "the depot holds 20 crates", "log/b")
    mem.semantic.supersede(a, b, principal="t", reason="uno")
    mem.semantic.quarantine_fact(b, reason="banco")

    ch = retirement_breakdown(mem.semantic)["chain"]
    assert ch["ends_servable"] == 0 and ch["ends_dead"] == 1, ch


def test_l_aggregato_NON_esce_senza_lo_split_per_motivo(mem):
    """La regola nata da questa misura: un numero che si ribalta quando lo
    dividi non si consegna da solo. Sul corpus reale l'aggregato dice 37%
    e `same-source evolution` dice 100%."""
    a = _f(mem, "the depot holds 10 crates", "log/a")
    b = _f(mem, "the depot holds 20 crates", "log/b")
    mem.semantic.supersede(a, b, principal="t", reason="evoluzione")

    ch = retirement_breakdown(mem.semantic)["chain"]
    voci = {v["reason"]: v for v in ch["by_reason"]}
    assert voci["evoluzione"]["n"] == 1
    assert voci["evoluzione"]["ends_servable"] == 1
    assert "chain" in ch["formula"].lower()


def test_un_ciclo_non_manda_in_loop_e_si_dichiara(mem):
    """Il prodotto vieta i cicli e sul corpus reale sono zero, ma un
    registro che si impianta su un dato sporco e' peggio di uno che lo
    dichiara."""
    a = _f(mem, "the depot holds 10 crates", "log/a")
    b = _f(mem, "the depot holds 20 crates", "log/b")
    mem.semantic.supersede(a, b, principal="t", reason="uno")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("UPDATE facts SET superseded_by = ?, superseded_at = ? "
                    "WHERE id = ?", (a, time.time(), b))

    ch = retirement_breakdown(mem.semantic)["chain"]
    assert ch["cycles"] >= 1, ch
