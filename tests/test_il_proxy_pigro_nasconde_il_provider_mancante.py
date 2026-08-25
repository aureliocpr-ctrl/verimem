"""`verify.sufficiency` deve dire «mi manca una dipendenza», non «sono guasto».

Il dossier promette all'utente di dichiarare cosa ha DAVVERO girato, e il codice
di `trust_report` distingue apposta due stati che chiedono all'utente due azioni
opposte — lo dice il suo stesso commento:

    «`no_provider` = un llm c'e' ma e' il MOCK che `get_llm()` restituisce quando
    nessun provider e' configurato: chiamarlo produce un verdetto illeggibile, e
    dire "unreadable" farebbe sembrare un guasto cio' che e' una DIPENDENZA
    MANCANTE.»

Chi legge `unreadable` va a cercare un bug; chi legge `no_provider` installa il
pezzo che manca.

IL DIFETTO, misurato alla porta MCP il 25/08 su una macchina senza provider:
`hippo_trust_report` risponde `sufficiency: "unreadable"`. La guardia esiste e
funziona — su `MockLLM` scatta — ma la porta non le passa un `MockLLM`: le passa
`a.wake.llm`, che e' un **`LazyLLM`**, il proxy pigro. La guardia legge il nome
del PROXY invece di cio' che il proxy costruisce, e cade nel ramo sbagliato.

⚠️ E la giuntura era prevista e verificata — dal lato del proxy. `LazyLLM` dice:

    «No ``isinstance`` checks are done on the llm in the wake/sleep hot paths
    (verified), so a proxy is safe here.»

Vero quando fu scritto (06/06). Il controllo sul tipo e' arrivato dopo, in un
altro file, e per giunta come confronto sul NOME — che non si trova nemmeno
cercando `isinstance`. ⇒ **Una precondizione dichiarata che nessuno ricontrolla
quando cambia il codice a cui si riferisce.**
"""
from __future__ import annotations

import time

from verimem.llm import LazyLLM, get_llm
from verimem.semantic import Fact, SemanticMemory
from verimem.trust_report import build_trust_report

_DOMANDA = "Client Rossi budget"


def _store_con_qualcosa_dentro(tmp_path) -> SemanticMemory:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(id="p-1", topic="client/rossi",
                  proposition="Client Rossi's budget is 500k",
                  asserted_at=time.time()), embed="sync")
    return sm


def test_il_valore_atteso_e_raggiungibile(tmp_path):
    """Controllo POSITIVO del righello: senza di questo il test sotto potrebbe
    pretendere uno stato che il codice non produce in nessun caso, e fallire
    per la ragione sbagliata."""
    rep = build_trust_report(_store_con_qualcosa_dentro(tmp_path), _DOMANDA,
                             k=3, llm=get_llm())
    assert rep["n_facts"] > 0, "senza hit il ramo del giudice non parte"
    assert rep["verify"]["sufficiency"] == "no_provider", (
        "passando direttamente il mock lo stato no_provider deve uscire: "
        f"uscito {rep['verify']['sufficiency']!r}")


def test_un_proxy_pigro_non_deve_far_sembrare_un_guasto_una_dipendenza_mancante(
        tmp_path):
    """RED prima della cura: `LazyLLM` risolve al mock, quindi il provider
    MANCA — e il dossier deve dirlo con la parola giusta."""
    rep = build_trust_report(_store_con_qualcosa_dentro(tmp_path), _DOMANDA,
                             k=3, llm=LazyLLM())

    #: ⛔ PRESIDIO CONTRO LA CELLA MUTA: il ramo che assegna lo stato gira
    #: SOLO se ci sono hit. Senza questa riga un recall a vuoto darebbe
    #: `sufficiency == "off"` e il test fallirebbe raccontando un'altra storia
    #: — oppure, peggio, passerebbe misurando il nulla.
    assert rep["n_facts"] > 0, (
        "nessun fatto recuperato: il ramo del giudice non e' stato eseguito e "
        "questa cella NON sta misurando cio' che dice di misurare")

    assert rep["verify"]["sufficiency"] == "no_provider", (
        "con un LazyLLM che risolve al mock il dossier deve dire "
        "«manca il provider», non «verdetto illeggibile»: uscito "
        f"{rep['verify']['sufficiency']!r}")
