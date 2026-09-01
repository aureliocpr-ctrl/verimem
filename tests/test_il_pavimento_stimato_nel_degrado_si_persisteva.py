"""Un pavimento stimato mentre l'encoder è freddo vale `0.0`, e veniva SCRITTO.

Il caso vero, dallo store di Aurelio (documento `60`): il file conteneva
``{"floor": 0.0, "n_facts": 13795}`` dalle 20:32:08 del 30/08 alle 02:52:23 del
31/08 — **sei ore con il pavimento spento** su un corpus di quasi quattordicimila
fatti.

⚠️ **Tredicimila fatti non sono «uno store troppo piccolo per misurare»**, che è
l'unico caso in cui `estimate_relevance_floor` documenta lo zero: *«0.0 (floor
off) when the store is too small to measure — a floor guessed from nothing would
be worse than none»*. Lì lo zero è una scelta; qui è un incidente con la stessa
faccia.

LA CATENA, e ogni anello è già documentato altrove nel repo:

    estimate_relevance_floor  misura chiamando `sm.recall` su 32 sonde
    recall degradato          sul ramo keyword assegna `score 0.0` a TUTTI
                              (`hits_2t = [(f, 0.0) for f in kw]`)
    quindi                    ogni sonda ha massimo 0.0 → il quantile è 0.0
    e quello zero             finisce su disco, e ci resta finché il corpus
                              non deriva del 5% (`_FLOOR_DRIFT`)

Quello zero significa **«non misurato»**, non «nessun rumore» — la stessa
distinzione per cui esiste `test_il_pavimento_tagliava_un_ranking_degradato`,
che però cura la LETTURA. Qui si cura la SCRITTURA: una lettura degradata
riguarda una query, un pavimento degradato **persistito** riguarda tutte quelle
che seguono.

🔑 E lo zero persistito non è inerte: è **falsy**, quindi nei siti che lo
controllano con un `if` si comporta da «nessun pavimento» invece che da
«pavimento a zero».

Il contatore `_recall_degraded_count` **esiste già** — è nato perché «il degrado
cold-encode era invisibile al caller» — ed è già letto da `client.recall` per
questa identica ragione. Nessuno lo leggeva dalla stima: dodicesima istanza di
«il meccanismo c'è, il chiamante non lo alimenta».
"""
from __future__ import annotations

import json

import pytest

import verimem.semantic as sem
from verimem.client import Memory


@pytest.fixture()
def registro(tmp_path):
    m = Memory(str(tmp_path / "reg.db"))
    for i in range(1, 12):
        m.add(f"Il magazzino K-{70 + i} di Rovigo ha {4000 + i * 100} "
              f"metri quadrati.", topic="az/mag")
    return m


@pytest.fixture()
def degradato(monkeypatch):
    """Forza il ramo keyword: la stessa strada che il codice prende da solo
    quando il daemon di encode è freddo o conteso."""
    monkeypatch.setattr(sem, "_encode_prepared_within_budget",
                        lambda *a, **k: None)


def test_un_pavimento_stimato_nel_degrado_non_si_persiste(registro, degradato):
    """IL CUORE: la stima fatta a encoder freddo non deve finire su disco.

    Senza questa guardia il file resta a zero per ore — misurato sei, sul corpus
    vero — e ogni lettura successiva serve un pavimento che non è mai stato
    misurato.
    """
    registro._floor_cache = None
    registro._auto_relevance_floor()

    f = registro._floor_file()
    if f.exists():
        salvato = json.loads(f.read_text(encoding="utf-8"))
        assert salvato.get("floor"), (
            "un pavimento stimato durante un degrado è stato PERSISTITO: "
            f"{salvato}"
        )


def test_nel_degrado_il_valore_torna_lo_stesso(registro, degradato):
    """IL FAIL-OPEN. Non persistere non vuol dire rompere: la chiamata deve
    restituire un numero, perché tutto questo percorso è dichiarato
    fail-open — «il valore salvato è un'ottimizzazione, non un dato»."""
    registro._floor_cache = None
    val = registro._auto_relevance_floor()
    assert isinstance(val, float)


def test_nel_degrado_non_si_congela_nemmeno_in_cache(registro, degradato):
    """Il disco non basta: se lo zero degradato resta nella cache di istanza,
    la prossima chiamata lo serve lo stesso per tutto il TTL, e la cura
    varrebbe solo per il processo successivo."""
    registro._floor_cache = None
    registro._auto_relevance_floor()
    assert not (registro._floor_cache and registro._floor_cache[1] == 0.0), (
        "lo zero degradato è rimasto nella cache di istanza: "
        f"{registro._floor_cache}"
    )


def test_a_caldo_il_pavimento_si_persiste_ancora(registro):
    """IL PRESIDIO — e serve a dimostrare che la cura non spegne la funzione.

    Fuori dal degrado il file si scrive come prima, con il marcatore di
    metrica che la migrazione dichiarata esige. ⚠️ Questo test resta verde
    anche TOGLIENDO la cura: è il suo mestiere, tiene fermo ciò che non deve
    cambiare.
    """
    registro._floor_cache = None
    registro._auto_relevance_floor()

    f = registro._floor_file()
    assert f.exists(), "a caldo il pavimento non è stato persistito affatto"
    salvato = json.loads(f.read_text(encoding="utf-8"))
    assert salvato.get("n_metric") == "servibili", salvato
    assert "n_facts" in salvato, salvato
