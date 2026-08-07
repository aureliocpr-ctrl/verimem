"""La stessa domanda dei ritiri, girata alla quarantena — con esito opposto.

Sui ritiri la distribuzione ha ribaltato la storia: un'ora sola conteneva
il 92%. Ho fatto la stessa domanda alla quarantena e la risposta è **no**,
e va detto perché un negativo misurato vale quanto una cura:

    quarantinati vivi 705 · giorno più affollato 88 (12.5%)

Nessun evento: è distribuita, quindi «tasso di quarantena» è una parola
giusta — al contrario di «tasso di ritiro», che non lo era.

⚠️ Ma la stessa query mostra un'altra cosa, che nessuna superficie diceva:
**il tasso oscilla di venti volte fra un giorno e l'altro.**

    scritti 621 · quarantinati 68 (11.0%)  2026-08-04
    scritti 473 · quarantinati 35 ( 7.4%)  2026-08-05
    scritti 430 · quarantinati  1 ( 0.2%)  2026-05-31
    scritti 384 · quarantinati  2 ( 0.5%)  2026-05-30

Un singolo numero — «il 10.2% viene quarantinato» — descrive gli ultimi
giorni e non il prodotto. ⛔ Il PERCHÉ non lo tocco: può essere il gate
che è cambiato o cosa scriviamo che è cambiato, e distinguerli è del
write path. Qui si mostra la serie, non la causa.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from verimem.client import Memory
from verimem.retirement_log import quarantine_breakdown

_GIORNO = 86400.0


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "m.db")


def _scrivi(m: Memory, testo: str, topic: str, *, quando: float,
            quarantina: bool = False) -> str:
    fid = m.add(testo, topic=topic)["id"]
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET created_at = ? WHERE id = ?",
                    (quando, fid))
    if quarantina:
        m.semantic.quarantine_fact(fid, reason="banco")
    return fid


def test_il_giorno_porta_scritti_E_quarantinati_perche_serve_il_rapporto(mem):
    """Il conteggio da solo non dice niente: 68 quarantinati su 621 e 68
    su 100 sono due prodotti diversi."""
    ora = time.time()
    for i in range(3):
        _scrivi(mem, f"the depot {i} holds crates", f"log/{i}", quando=ora,
                quarantina=(i == 0))

    out = quarantine_breakdown(mem.semantic)
    riga = out["by_day"][0]
    assert riga["written"] == 3 and riga["quarantined"] == 1
    assert riga["rate"] == pytest.approx(1 / 3, abs=0.01)


def test_dichiara_la_CONCENTRAZIONE_anche_quando_dice_che_non_ce_n_e(mem):
    """Il campo è lo stesso dei ritiri e serve nei DUE versi: là mostrava
    un evento, qui deve poter mostrare che un evento non c'è."""
    ora = time.time()
    _scrivi(mem, "the depot holds 10 crates", "log/a", quando=ora,
            quarantina=True)
    _scrivi(mem, "the depot holds 20 crates", "log/b",
            quando=ora - 5 * _GIORNO, quarantina=True)

    c = quarantine_breakdown(mem.semantic)["concentration"]
    assert c["share"] == pytest.approx(0.5, abs=0.01), c
    assert "busiest day" in c["formula"].lower()


def test_un_corpus_senza_quarantene_non_inventa_un_tasso(mem):
    mem.add("the head office is in Milan", topic="hq")
    out = quarantine_breakdown(mem.semantic)
    assert out["quarantined"] == 0
    assert out["by_day"] == []
    assert out["concentration"]["share"] is None


def test_i_quarantinati_RITIRATI_non_si_contano_due_volte(mem):
    """Un fatto quarantinato e poi ritirato è già contato fra i ritiri: il
    quartetto tiene le tre uscite separate per costruzione, e questa vista
    deve usare la stessa definizione."""
    ora = time.time()
    a = _scrivi(mem, "the depot holds 10 crates", "log/a", quando=ora,
                quarantina=True)
    b = _scrivi(mem, "the depot holds 20 crates", "log/b", quando=ora)
    mem.semantic.supersede(a, b, principal="t", reason="banco")

    assert quarantine_breakdown(mem.semantic)["quarantined"] == 0


def test_la_serie_esce_in_ordine_di_grandezza_come_per_i_ritiri(mem):
    ora = time.time()
    for i in range(3):
        _scrivi(mem, f"the yard {i} holds pallets", f"y/{i}", quando=ora,
                quarantina=True)
    _scrivi(mem, "the yard nine holds pallets", "y/9",
            quando=ora - 3 * _GIORNO, quarantina=True)

    giorni = quarantine_breakdown(mem.semantic)["by_day"]
    assert giorni[0]["quarantined"] == 3 and giorni[1]["quarantined"] == 1
