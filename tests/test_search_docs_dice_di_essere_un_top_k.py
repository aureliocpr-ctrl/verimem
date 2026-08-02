"""`search-docs` restituisce sempre qualcosa, e non lo diceva.

Trovato usando il prodotto: indicizzato un listino prezzi e fatte due domande.

    «quanto costa il piano annuale»              -> chunk a 0.884
    «quale database usa il cluster di produzione» -> LO STESSO chunk a 0.757

La seconda domanda non compare nel documento nemmeno per una parola, e la
risposta è identica alla prima: stesso testo, stessa citazione esatta,
punteggio poco più basso. Chi legge vede una fonte precisa e conclude di aver
avuto una risposta.

Il resto del prodotto si astiene — «abstention over hallucination» è la riga
di apertura — perché ha un pavimento MISURATO. Qui non c'è, e inventarne uno a
occhio è l'errore già pagato il 30/07 con la soglia `max(floor, noise_floor)`:
scritta, misurata sul corpus vero e ritirata il giorno dopo perché rendeva
muta la mappa dell'ignoranza, 7 domande su 8 che il corpus sa rispondere.

Quindi due cose e nessuna soglia inventata: `--min-score` per chi sa che
taglio vuole, e una riga in fondo che dichiara la natura della lista a tutti
gli altri.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod


class _Indice:
    def __init__(self, punteggi):
        self._p = punteggi

    def search(self, query, k=5):
        return [{"score": s, "text": "Il piano annuale costa 100 euro.",
                 "source_id": "listino.md", "version": 1,
                 "start": 0, "end": 32} for s in self._p][:k]


@pytest.fixture()
def con_indice(monkeypatch):
    import verimem.document_index as di

    def _con(*punteggi):
        monkeypatch.setattr(di, "DocumentIndex",
                            lambda *a, **k: _Indice(list(punteggi)))
    return _con


def _cerca(*args):
    return CliRunner().invoke(cli_mod.app, ["search-docs", *args]).output


def test_la_lista_dichiara_di_essere_un_top_k(con_indice):
    con_indice(0.757)
    out = _cerca("quale database usa il cluster")
    basso = out.lower()
    assert "top-" in basso and ("non si astiene" in basso
                                or "not a verified" in basso), (
        f"la lista si legge come una risposta:\n{out}")


def test_min_score_taglia(con_indice):
    con_indice(0.884, 0.757)
    out = _cerca("quanto costa il piano", "--min-score", "0.8")
    assert "0.884" in out, out
    assert "0.757" not in out, out


def test_senza_min_score_non_taglia_niente(con_indice):
    """Il default resta quello di prima: il taglio giusto dipende dal corpus e
    questo comando non lo indovina."""
    con_indice(0.884, 0.757)
    out = _cerca("quanto costa il piano")
    assert "0.884" in out and "0.757" in out, out


def test_se_il_taglio_svuota_lo_dice(con_indice):
    con_indice(0.4, 0.3)
    out = _cerca("una domanda qualunque", "--min-score", "0.9")
    assert "no results" in out, out
