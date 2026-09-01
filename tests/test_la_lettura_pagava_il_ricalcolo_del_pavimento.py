"""Una lettura qualunque poteva pagare il ricalcolo del pavimento.

IL COSTO, misurato da altri sul corpus vero (`W2-257`, 14382 fatti)::

    lettura del file persistito       3 ms
    ricalcolo a 32 sonde         24 169 ms      <- rapporto 8067x

E il ricalcolo NON stava in un ramo raro: `client.py` chiama
`_auto_relevance_floor()` per costruire l'avviso di rilevanza **a ogni
`search`**, fuori da ogni `if`. Quindi quando il file persistito e' stantio —
la deriva supera `_FLOOR_DRIFT = 0,05`, cioe' ~658 fatti su 13166 — **la prima
ricerca qualunque paga il ricalcolo**, anche una che non chiede nessun
pavimento e non taglia niente.

⚖️ INTERESSE DICHIARATO: la chiamata dentro l'avviso non e' mia (`0291bf03`,
verificato con `git log -S`), ma il pezzo (i) l'ha ereditata e ci ha costruito
sopra, e il pezzo (iv) — che si chiama *lettura-senza-ricalcolo* — prometteva
di toglierla dal percorso dell'utente senza averlo fatto.

🔑 LA CURA, ed e' quella che il pezzo prometteva: **la lettura non ricalcola.**
Se un valore persistito esiste lo serve anche quando e' stantio, perche' un
pavimento vecchio e' un'approssimazione di uno nuovo, mentre 24 secondi dentro
una richiesta sono un guasto. Il ricalcolo resta possibile e diventa
ESPLICITO: lo chiede chi ha il costo atteso (`doctor`, un warmup, un daemon),
passando `rinfresca=True`.

⚠️ COSA RESTA VERO ANCHE DOPO: la primissima lettura di uno store senza file
paga la stima. E' una volta per store, non a ogni deriva, ed e' l'unico modo di
avere un pavimento la prima volta.

⚠️ PERCHE' SI CONTANO LE CHIAMATE E NON I MILLISECONDI. Su uno store di prova
la stima costa pochi ms: cronometrare misurerebbe il rumore. La domanda vera e'
BINARIA — «la lettura ha ricalcolato, si' o no?» — e si risponde contando le
chiamate alla funzione costosa. I 24169 ms sono il prezzo di UNA chiamata sul
corpus vero, e stanno nella cella di chi li ha misurati.
"""

from __future__ import annotations

import json

import pytest

import verimem.relevance_floor as rf
from verimem.client import Memory


@pytest.fixture()
def memoria(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    return Memory(str(tmp_path / "s.db"))


@pytest.fixture()
def conta(monkeypatch):
    """Quante volte e' stata chiamata la stima costosa.

    ⚠️ Si patcha `verimem.relevance_floor`, non `verimem.client`: la client
    importa la funzione DENTRO il metodo, quindi risolve il nome sul modulo
    ogni volta. Patchare il punto sbagliato darebbe zero chiamate sempre — un
    verde che non misura niente.
    """
    n = {"chiamate": 0}
    vera = rf.estimate_relevance_floor

    def _spia(*a, **k):
        n["chiamate"] += 1
        return vera(*a, **k)

    monkeypatch.setattr(rf, "estimate_relevance_floor", _spia)
    return n


def _invalida(mem, *, n_facts=99999):
    """Rende il file persistito STANTIO senza toccarne il valore.

    Si scrive `n_facts` lontano dal conteggio vero: e' esattamente cio' che fa
    il corpus quando cresce. La cache in-process va azzerata, altrimenti il TTL
    di 300 s risponde prima che il file venga guardato — e il banco misurerebbe
    la cache.
    """
    f = mem._floor_file()
    f.write_text(json.dumps(
        {"floor": 0.4242, "n_facts": n_facts, "n_metric": "servibili"}),
        encoding="utf-8")
    mem._floor_cache = None


def test_la_premessa_il_pavimento_si_calcola_e_si_persiste(memoria, conta):
    """Controllo positivo del banco: senza file la stima viene chiamata, e il
    file compare. Se questa cella cade, le altre misurano un'altra cosa."""
    memoria._floor_cache = None
    memoria._auto_relevance_floor()
    assert conta["chiamate"] == 1, (
        f"la stima non e' stata chiamata su uno store senza file persistito: "
        f"{conta}")
    assert memoria._floor_file().exists(), (
        "il valore non e' stato persistito: la guardia sul file non puo' "
        "essere esercitata")


def test_CONTROLLO_col_file_VALIDO_la_lettura_non_ricalcola(memoria, conta):
    """La parte che gia' funzionava, e va tenuta ferma: quando il file e'
    coerente col corpus la lettura lo legge e basta."""
    memoria._floor_cache = None
    memoria._auto_relevance_floor()
    assert conta["chiamate"] == 1
    memoria._floor_cache = None
    memoria._auto_relevance_floor()
    assert conta["chiamate"] == 1, (
        f"il file era valido e la lettura ha ricalcolato lo stesso: {conta}")


def test_col_file_STANTIO_la_lettura_NON_deve_ricalcolare(memoria, conta):
    """IL CUORE. Il corpus e' cresciuto oltre la deriva: prima di questa cura
    la lettura buttava il valore e ne ricalcolava uno nuovo — 24 secondi, sul
    corpus vero, dentro la richiesta di chi stava solo cercando."""
    memoria._floor_cache = None
    memoria._auto_relevance_floor()
    assert conta["chiamate"] == 1
    _invalida(memoria)

    val = memoria._auto_relevance_floor()

    assert conta["chiamate"] == 1, (
        "la lettura ha ricalcolato il pavimento perche' il corpus era "
        f"cresciuto: e' il costo che il pezzo (iv) doveva togliere. {conta}")
    assert val == pytest.approx(0.4242), (
        f"servito {val} invece del valore persistito: la lettura deve usare il "
        "pavimento che ha, anche quando e' vecchio")


def test_il_valore_servito_si_sa_che_e_STANTIO(memoria, conta):
    """⚠️ SERVIRE UN VALORE VECCHIO IN SILENZIO SAREBBE LA CLASSE CHE CURIAMO.
    Chi serve un'approssimazione deve poter dire che lo e', altrimenti «vecchio
    di sei ore» e «appena misurato» diventano la stessa cosa — ed e' successo:
    `{"floor": 0.0}` e' rimasto per SEI ORE su quasi quattordicimila fatti.

    Non e' un campo nella risposta di `search` (sarebbe un contratto nuovo per
    chi la chiama): e' uno stato leggibile da chi deve decidere se rinfrescare.
    """
    memoria._floor_cache = None
    memoria._auto_relevance_floor()
    assert getattr(memoria, "_floor_stantio", None) is False, (
        "appena calcolato, il pavimento non e' stantio")
    _invalida(memoria)
    memoria._auto_relevance_floor()
    assert getattr(memoria, "_floor_stantio", None) is True, (
        "il pavimento servito e' vecchio e nulla lo dichiara: chi deve "
        "rinfrescarlo non ha modo di sapere che serve")


def test_chi_ha_il_costo_ATTESO_puo_chiedere_il_ricalcolo(memoria, conta):
    """⚖️ L'ALTRA META' DELLA CURA. Se la lettura non ricalcola mai, qualcuno
    deve poterlo fare: `doctor`, un warmup, un daemon — dove 24 secondi sono
    attesi e non sorprendono nessuno. Senza questa strada la cura non sposta il
    costo, lo cancella, e il pavimento resterebbe vecchio per sempre."""
    memoria._floor_cache = None
    memoria._auto_relevance_floor()
    assert conta["chiamate"] == 1
    _invalida(memoria)

    memoria._auto_relevance_floor(rinfresca=True)

    assert conta["chiamate"] == 2, (
        f"il rinfresco esplicito non ha ricalcolato: {conta}")
    memoria._floor_cache = None
    assert getattr(memoria, "_floor_stantio", None) is False, (
        "dopo un rinfresco il valore non e' piu' vecchio")
