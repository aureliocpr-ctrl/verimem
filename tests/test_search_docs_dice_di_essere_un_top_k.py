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
    """🪞 RAFFORZATA il 2026-09-01 alle 22:20: la cella si chiamava gia' cosi'
    e verificava solo `"no results" in out` — cioe' passava col messaggio «no
    results (index empty or no match)», che qui e' una CAUSA SBAGLIATA: l'indice
    non e' vuoto e il match c'era, l'ha tolto la soglia che l'utente ha chiesto.

    🔑 Un presidio col nome giusto che non verifica quel nome e' peggio della
    sua assenza: chi lo legge crede che il caso sia coperto. Ora la cella
    pretende che il messaggio nomini la SOGLIA."""
    con_indice(0.4, 0.3)
    out = _cerca("una domanda qualunque", "--min-score", "0.9")
    assert "no results" in out, out
    basso = out.lower()
    assert "0.9" in out and ("min-score" in basso or "threshold" in basso), (
        "il comando dice «no results» senza nominare la soglia che ha tolto "
        f"tutto: chi legge conclude che il corpus non sa rispondere.\n{out}")
    assert "index empty" not in basso, (
        "il messaggio attribuisce il vuoto a un indice vuoto o a un match "
        f"mancante, mentre la causa e' il taglio:\n{out}")


def test_un_taglio_PARZIALE_si_dichiara_come_gia_fa_quello_per_injection(
        con_indice):
    """IL GEMELLO DEL DIFETTO CURATO SULLA PORTA (`92333f82`), trovato con lo
    sweep «chi altro taglia per punteggio?».

    ⚠️ E il controllo positivo sta a due centimetri, nella STESSA funzione: i
    chunk nascosti per injection vengono dichiarati sia quando svuotano
    («were HIDDEN») sia quando no («results below are PARTIAL»). Il taglio per
    `--min-score` non diceva niente in nessuno dei due casi.

    ⇒ Una lista accorciata dell'80%% si legge identica a una lista intera, e
    l'assenza dell'avviso si legge come «non ha tagliato»."""
    con_indice(0.884, 0.757, 0.4)
    out = _cerca("quanto costa il piano", "--min-score", "0.8")
    assert "0.884" in out, out
    basso = out.lower()
    assert "partial" in basso or "parziale" in basso, (
        "due chunk su tre sono stati tolti dalla soglia e la lista non lo "
        f"dichiara, mentre per i chunk nascosti lo fa:\n{out}")
    assert "2" in out, f"non dice QUANTI ne ha tolti:\n{out}"


def test_CONTROLLO_senza_taglio_nessun_avviso_di_parzialita(con_indice):
    """⚠️ LA POPOLAZIONE OPPOSTA: un avviso sempre acceso e' rumore con l'aria
    di un dato. Se nulla e' stato tolto, la lista non deve dirsi parziale."""
    con_indice(0.884, 0.757)
    out = _cerca("quanto costa il piano")
    basso = out.lower()
    assert "partial" not in basso and "parziale" not in basso, (
        f"la lista si dichiara parziale senza che sia stato tolto nulla:\n{out}")
