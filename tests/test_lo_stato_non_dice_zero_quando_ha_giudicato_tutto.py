"""L'odometro non dice «0% dei fatti» proprio quando il gate li ha giudicati tutti.

`verimem stats` intesta le azioni del gate con la quota di fatti che la finestra
del registro copre — il registro parte dal giorno in cui fu aggiunto, e ciò che
precede gli è invisibile. La quota si calcola confrontando `facts.created_at` con
`MIN(trust_ledger.ts)`.

Ma il fatto viene scritto PRIMA della riga che ne registra l'ammissione: misurati
58 millisecondi su uno store nuovo. Confrontati senza margine, il fatto stesso che
ha APERTO il registro cade fuori dal registro, e uno store con un fatto solo si
sente rispondere:

    Gate actions (recorded since 2026-08-17, 0% of stored facts)
      admitted: 1
    Moat coverage  1/1 facts entailment-judged (100.0%)

— «0%» e «1/1 (100.0%)» nella stessa schermata. Il caso peggiore è la prima
installazione: la quota è sbagliata al massimo quando lo store è più piccolo, e
l'errore si diluisce man mano che cresce.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.cli import _ledger_window


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Uno store minimo con le due sole tabelle che la funzione legge."""
    def _costruisci(scarto: float, n_fatti: int = 1):
        db = tmp_path / "semantic" / "semantic.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        if db.exists():
            db.unlink()
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE facts (id TEXT, created_at REAL)")
        con.execute("CREATE TABLE trust_ledger (id INTEGER, ts REAL)")
        istante = 1786960660.5328684  # l'istante reale della misura
        con.execute("INSERT INTO trust_ledger VALUES (1, ?)", (istante,))
        for i in range(n_fatti):
            con.execute("INSERT INTO facts VALUES (?, ?)", (f"f{i}", istante - scarto))
        con.commit()
        con.close()
        monkeypatch.setattr("verimem._compat.data_dir", lambda: tmp_path)
        return db

    return _costruisci


def test_un_fatto_scritto_appena_prima_della_sua_riga_conta_come_coperto(store):
    """I 58 ms fra la scrittura e la sua registrazione non escludono il fatto."""
    store(scarto=0.058)
    _, quota = _ledger_window({})
    assert quota == pytest.approx(100.0), (
        f"un fatto scritto 58 ms prima della riga che ne registra l'ammissione deve "
        f"contare come coperto: la quota è {quota}. Con questo numero uno store appena "
        f"installato legge «0% of stored facts» mentre il gate ha giudicato tutto.")


def test_un_fatto_di_un_giorno_prima_resta_fuori(store):
    """Il margine non deve inghiottire ciò che il registro davvero non ha visto."""
    store(scarto=86_400.0)
    _, quota = _ledger_window({})
    assert quota == pytest.approx(0.0), (
        f"un fatto scritto un giorno prima della prima riga del registro NON è coperto, "
        f"e la quota deve dirlo: vale {quota}. Un margine che lo includesse renderebbe "
        f"l'intestazione una rassicurazione invece di una misura.")


def test_il_margine_e_stretto_quanto_serve(store):
    """Due secondi sono già «prima»: il margine copre il ritardo di scrittura, non di più."""
    store(scarto=2.0)
    _, quota = _ledger_window({})
    assert quota == pytest.approx(0.0), (
        f"a due secondi di distanza il fatto precede il registro e la quota deve valere 0, "
        f"non {quota}: se il margine crescesse fino a coprirlo, smetterebbe di distinguere "
        f"«scritto insieme» da «scritto prima».")
