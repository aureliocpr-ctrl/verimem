"""`/v1/correct` — la rotta che si chiama *guardian* — non si asteneva mai.

TROVATO DA WS4 facendo dogfooding sull'API HTTP, e verificato qui: stesso
store, stessa domanda senza risposta, tre rotte, tre comportamenti.

    GET /v1/search   2 hit, top «La riunione settimanale è il martedì» a 0.8227
                     (corretto: search restituisce ciò che trova, è il suo mestiere)
    GET /v1/explain  abstained=TRUE, n_facts=0
    GET /v1/correct  verdict=ACCEPT, answer=«La riunione settimanale è il martedì
                     alle 10.»  ← a una domanda sul LOGO aziendale

Il retrieval è lo stesso — `search` lo dimostra, due hit a 0.82 per entrambe.
A cambiare è **una riga**: in `gateway.py` `min_relevance=_gateway_min_relevance()`
compare **una volta sola** in tutto il file, sulla rotta `explain`. E
`guardian.correct_read` non ha nemmeno il parametro.

Il docstring del pavimento dichiara che è il punto del prodotto — «Making the
enterprise API abstain by default is the point of a TRUST product» — e la rotta
esplicitamente chiamata *guardiano* era l'unica lettura che non lo applicava.
ws4 ha misurato che cosa costa e cosa rende, su entrambe le popolazioni:

                        | domande CON risposta | domande SENZA risposta
      senza pavimento   |      10 / 10   ✓     |      10 / 10   ✗
      con pavimento     |       9 / 10         |       0 / 10   ✓

Una risposta vera persa su dieci, dieci risposte false bloccate su dieci. Per
una memoria che vende l'astensione, quello scambio è il prodotto.

⚠️ LA CURA È UN PARAMETRO, NON UNA RISCRITTURA — e questo è il punto: il ramo
di astensione **esiste già** e ha il suo `reason` («no_support»), scritto quando
`hits` è vuoto. Mancava solo che qualcosa svuotasse `hits`. Chi legge questo
file resistendo alla tentazione di aggiungere logica: non serve, guarda le
prime righe di `correct_read`.

⚠️ IL PRESIDIO CHE RENDE LA CURA NON UN INTERRUTTORE: una domanda a cui il
corpus SA rispondere deve continuare a ricevere la risposta. Un guardiano che
si astiene sempre è inutile quanto uno che non si astiene mai.
"""
from __future__ import annotations

import pytest

from verimem import Memory
from verimem.guardian import correct_read


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Uno store d'ufficio: due argomenti, nessuno dei quali è il logo."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(tmp_path))
    m = Memory()
    m.add("Il server di produzione si chiama nexus.", topic="ufficio/server")
    m.add("La riunione settimanale e' il martedi' alle 10.", topic="ufficio/riunioni")
    return m


def test_una_domanda_senza_risposta_non_riceve_un_fatto_scorrelato(store):
    """Il cuore: sul logo il corpus non ha nulla, e il guardiano serviva la
    riunione. Servire un fatto scorrelato è peggio che tacere — chi legge non
    ha modo di sapere che la risposta non c'entra."""
    out = correct_read(store, "Di che colore e' il logo aziendale?",
                       min_relevance="auto")
    assert out["verdict"] == "ABSTAIN", (
        f"il guardiano risponde «{out.get('answer')}» a una domanda sul logo")
    assert out["answer"] is None


def test_una_domanda_CON_risposta_continua_a_essere_servita(store):
    """IL PRESIDIO. Un guardiano che si astiene sempre non è più utile di uno
    che non si astiene mai: la cura deve costare poco sul verso buono."""
    out = correct_read(store, "Come si chiama il server di produzione?",
                       min_relevance="auto")
    assert out["verdict"] != "ABSTAIN", (
        "la risposta e' nel corpus e il guardiano si astiene comunque")
    assert "nexus" in (out.get("answer") or "").lower()


def test_senza_pavimento_il_comportamento_storico_non_cambia(store):
    """La compatibilità: chi passa `off` (o non passa nulla) ottiene ciò che
    otteneva prima. Il pavimento e' una MANOPOLA, non un cambio di semantica —
    lo dice il docstring di `_gateway_min_relevance`."""
    out = correct_read(store, "Di che colore e' il logo aziendale?",
                       min_relevance=None)
    assert out["verdict"] != "ABSTAIN"


def test_l_astensione_dice_COSA_c_era_e_non_tace_soltanto(store):
    """IL PRESIDIO CHE HA CORRETTO LA PRIMA STESURA DELLA CURA.

    Passare il pavimento a `mem.search` sembrava la mossa ovvia e ha rotto
    `test_correct_abstains_on_real_conflict`: quando due fatti si
    contraddicono, questo endpoint si astiene **mostrando entrambi i lati**, e
    col filtro davanti al retrieval i contendenti sparivano prima di essere
    visti. L'astensione restava, ma spariva l'informazione più preziosa che il
    guardiano possa dare — *ci sono due fatti in conflitto, eccoli*.

    Perciò il pavimento decide se SERVIRE, non se VEDERE: chi si astiene per
    scarsa pertinenza deve comunque dire cosa aveva trovato, e con un `reason`
    distinto da «non c'era niente»."""
    out = correct_read(store, "Qual e' la ricetta della carbonara?",
                       min_relevance="auto")
    assert out["verdict"] == "ABSTAIN"
    assert out["reason"] == "below_relevance_floor", (
        "«non c'era niente» e «c'era ma non era pertinente» sono due risposte "
        "diverse, e chi legge ha diritto di distinguerle")
    assert out["evidence"], "l'astensione tace su cio' che aveva trovato"
