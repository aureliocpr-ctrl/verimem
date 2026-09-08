"""La porta degli agenti non dice PERCHE' ha tolto: DUE cause su quattro.

2026-09-08. `Risultati` dichiara quattro cause di risposta ridotta e l'SDK le
serve tutte con i numeri. `hippo_facts_recall` chiama `a.semantic.recall(...)`
direttamente e non passa da `Memory.search`, dove quelle dichiarazioni vivono.

NON E' UNA SCOPERTA NUOVA CHE SIA UNA CLASSE: sta scritta in `mcp_server.py`
sopra due cure precedenti, con le stesse parole — «questo handler chiama
`a.semantic` direttamente e non passa da `Memory.search`, quindi la cura di
un'ora prima non lo raggiungeva» (pavimento, terza generazione) e «⚠️ QUARTA
GENERAZIONE DELLA STESSA CURA […] per lo stesso identico motivo» (ranking
degradato). Ogni volta si e' curato IL CASO TROVATO, e ogni volta il successivo
e' arrivato dallo stesso buco.

⚠️ QUESTO FILE ESISTE PER ROMPERE QUELLA SERIE, e per farlo NON cura: mette la
lista sotto presidio. I due casi rossi sono `xfail(strict=True)`, cioe' il
giorno in cui qualcuno li cura questo file diventa ROSSO e obbliga a togliere il
marcatore — che e' il solo modo in cui una lista di debito non marcisce in
silenzio. Un TODO in un commento non ha mai fermato una sesta generazione.

MISURATO il 2026-09-08, da questo file (2 passed, 2 xfailed, EXIT=0):
    pavimento   [curato, 3a gen.]   arriva      <- il controllo del righello
    scaduti                         arriva
    eta                             NON ARRIVA
    viaggio nel tempo               NON ARRIVA

⚠️ IL NUMERO E' DUE, E PRIMA AVEVO SCRITTO TRE. Il banco che avevo usato
(`scratchpad/sweep_cosa_non_arriva_alla_porta_mcp.py`) apriva `Memory(db)` con
un path esplicito mentre la porta MCP legge lo store dalle variabili
d'ambiente: DUE STORE DIVERSI, l'SDK scriveva di qua e la porta leggeva di la'.
Taceva perche' non aveva i fatti, non perche' non sappia dichiararli. Lo stesso
banco aveva una seconda falla nel verso opposto — fra le spie del viaggio nel
tempo c'era `"2900"`, che e' un VALORE e non una dichiarazione, e bastava a far
risultare verde una porta che serve il fatto giusto e tace sul perche'.
🔑 Il primo errore rendeva il buco PIU' GRANDE, cioe' dava ragione a chi
misurava: e' il verso in cui un numero non fa attrito e nessuno lo urta. L'ha
fermato `strict=True`, che ha trasformato un falso «non arriva» in un XPASS
rumoroso cinque minuti dopo averlo scritto.

⚠️ IL CONTROLLO E' LA CELLA DEL PAVIMENTO, e non e' decorativo: e' l'unico dei
quattro che il codice dichiara curato su questo handler. Se anche lui risultasse
muto, il difetto starebbe nel modo in cui questo file LEGGE la porta — cerca
stringhe dentro un JSON — e non nel prodotto, e i due `xfail` sarebbero un
teatro. Finche' quel test e' verde, i due rossi parlano del prodotto.

⛔ Store in tempdir. Nessuna scrittura sul prodotto.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from verimem import mcp_server  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.semantic import Fact  # noqa: E402

_GIORNO = 86400.0


@pytest.fixture()
def store(tmp_path, monkeypatch):
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(tmp_path))
    return Memory()


async def _invoke(name: str, arguments: dict) -> str:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call",
                          params=CallToolRequestParams(name=name,
                                                       arguments=arguments))
    risultato = await handler(req)
    payload = risultato.root if hasattr(risultato, "root") else risultato
    return " ".join(c.text for c in payload.content if hasattr(c, "text"))


def _porta_mcp(query: str, **kw) -> str:
    return asyncio.run(_invoke("hippo_facts_recall",
                               {"query": query, "k": 10, **kw}))


def _due_porte(m: Memory, campo: str, query: str, spie: tuple, **kw):
    """Cosa dichiara l'SDK, e la porta degli agenti lo dichiara?

    ⚠️ IL PRIMO VALORE E' IL CONTROLLO POSITIVO DELLA CELLA. Se l'SDK non
    dichiara niente non c'e' niente che debba arrivare, e un «MCP tace» direbbe
    il falso: ogni test qui sotto lo asserisce PRIMA di guardare la porta.
    """
    ris = m.recall(query, k=10)
    testo = _porta_mcp(query, **kw)
    return getattr(ris, campo, None), any(s in testo for s in spie), testo


def test_CONTROLLO_il_pavimento_ARRIVA_alla_porta(store):
    """Il pavimento e' curato su questo handler: la porta lo dichiara.

    Se questo diventa rosso, i tre `xfail` qui sotto non provano niente sul
    prodotto — il difetto sarebbe nel modo in cui leggo la porta.
    """
    store.semantic.store(Fact(id="P1", proposition="Il tornello 42 era aperto.",
                              topic="t"), embed="sync")
    testo = _porta_mcp("quale e' la capitale amministrativa della Nuova Zelanda",
                       min_relevance=0.99)
    assert any(s in testo for s in
               ("pavimento", "min_relevance", "relevance", "floor")), (
        "la porta non dichiara nemmeno il pavimento, che il codice dice curato "
        f"qui («terza generazione»): allora e' questo file che non sa leggerla, "
        f"e i tre xfail accanto sono teatro. USCITA: {testo[:300]}")


def test_la_porta_dichiara_i_fatti_tolti_dalla_scadenza(store):
    """VERDE, e nasce da un mio errore di misura corretto dal presidio stesso.

    Questo test era `xfail(strict=True)` come i due qui sotto, perche' il banco
    da cui l'avevo ricavato diceva «NON ARRIVA». Al primo giro e' uscito XPASS —
    cioe' la porta LI DICHIARA — e l'A/B ha trovato il difetto nel MISURATORE:
    quel banco apriva `Memory(db)` con un path esplicito mentre la porta MCP
    legge lo store dalle variabili d'ambiente. Due store diversi: l'SDK scriveva
    di qua e la porta leggeva di la', quindi taceva perche' non aveva i fatti.

    🔑 Il righello sbagliava A FAVORE della mia tesi (rendeva il buco piu'
    grande), che e' il verso in cui un errore non fa attrito e nessuno lo urta.
    L'ha fermato `strict=True` in cinque minuti: senza, il falso «non arriva»
    sarebbe rimasto scritto.
    """
    ieri = time.time() - _GIORNO
    store.add("Il termostato della sala macchine si regola dal pannello B.",
              topic="t/scad",
              source="Il termostato della sala macchine si regola dal pannello B.",
              valid_until=ieri)
    sdk, mcp, testo = _due_porte(
        store, "esclusi_perche_scaduti",
        "come si regola il termostato della sala macchine",
        ("scadut", "expired", "valid_until"))
    assert sdk, "CONTROLLO POSITIVO SPENTO: l'SDK non dichiara la scadenza"
    assert mcp, f"la porta tace. USCITA: {testo[:300]}"


@pytest.mark.xfail(strict=True, reason=(
    "la porta degli agenti non dichiara i fatti nascosti dall'ETA'; l'SDK si. "
    "Quando qualcuno la cura, questo diventa XPASS: togli il marcatore."))
def test_la_porta_dichiara_i_fatti_nascosti_dall_eta(store):
    #: `created_at` e NON `asserted_at`: il decay guarda quello.
    store.semantic.store(Fact(id="E1", proposition="Il tornello 42 era aperto.",
                              topic="t",
                              created_at=time.time() - 365 * _GIORNO),
                         embed="sync")
    sdk, mcp, testo = _due_porte(
        store, "nascosti_dalla_freschezza", "il tornello 42 era aperto",
        ("freschezza", "age", "stale", "nascosti"))
    assert sdk, "CONTROLLO POSITIVO SPENTO: l'SDK non dichiara la freschezza"
    assert mcp, f"la porta tace. USCITA: {testo[:300]}"


@pytest.mark.xfail(strict=True, reason=(
    "la porta degli agenti non dichiara di aver risposto AL PASSATO; l'SDK si. "
    "Quando qualcuno la cura, questo diventa XPASS: togli il marcatore."))
def test_la_porta_dichiara_di_aver_risposto_al_passato(store):
    #: date FISSE: la domanda nomina «1 giugno 2024», e con ancore mobili lo
    #: scenario scivolerebbe sotto la domanda.
    _B = 1_700_000_000.0
    for fid, quando, testo_f in (
            ("A", _B, "Il canone e' 2400 euro."),
            ("B", _B + 100 * _GIORNO, "Il canone e' 2900 euro."),
            ("C", _B + 500 * _GIORNO, "Il canone e' 3400 euro.")):
        store.semantic.store(Fact(id=fid, proposition=testo_f, topic="t",
                                  asserted_at=quando), embed="sync")
    store.semantic.supersede("A", "B", principal="test:suite",
                             reason="same-source evolution")
    store.semantic.supersede("B", "C", principal="test:suite",
                             reason="same-source evolution")
    sdk, mcp, testo = _due_porte(
        store, "letto_al_passato", "cosa risultava sul canone al 1 giugno 2024",
        #: ⚠️ NIENTE "2900" FRA LE SPIE: e' un VALORE, non una dichiarazione.
        #: Una spia che accetta il valore dice «arriva» anche a una porta che
        #: serve il fatto giusto e tace sul perche' — cioe' misura il contrario
        #: di quello che questo file presidia. Cercato in un banco parallelo,
        #: quel "2900" bastava a far risultare la cella verde.
        ("passato", "as_of", "scartati", "letto_al_passato"))
    assert sdk, "CONTROLLO POSITIVO SPENTO: l'SDK non dichiara il viaggio"
    assert mcp, f"la porta tace. USCITA: {testo[:300]}"
