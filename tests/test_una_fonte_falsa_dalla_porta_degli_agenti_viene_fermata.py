"""Le DUE vie di scrittura della porta MCP fermano una fonte che non regge?

2026-09-08. Reperto di @ws3 Galileo (post 4c475db1): due vie di scrittura MCP
NON passano da `Memory.add` — `mcp_server.py:843` (`_build_fact` costruisce il
Fact dentro il server) e la zona di `13648` (`a.semantic.store(fact)` diretto).
La constatazione e' esatta. La domanda che conta e' un'altra: **passano dal
gate anti-confab e dal moat?**

LETTO NEL CODICE, prima di eseguire (e' la parte che questo file poi falsifica):

  via A — `hippo_remember`
      13421  `_gate = run_validation_gate(..., source=_source,
              ground_write=_ground_write, claimant=_MCP_PRINCIPAL, ...)`
      13439  `if _gate.action == "reject": ... rejected_anti_confab`
      13453  `if _gate.action == "downgrade": -> status 'quarantined'`
      13539  `_build_fact(..., confidence_tier=_calcola_tier(_gate...))`
      13638  `a.semantic.store(fact)`

  via B — i `key_facts` di `hippo_record_episode`
      9487   `_kf_gate = _rvg(..., source=_kf_source,
              ground_write=True if _kf_source else None, ...)`
      9511   `if _kf_gate.action == "reject": ... continue`  (il fatto e' saltato)
      9522   `_build_fact(..., status='quarantined' if downgrade ...)`

Quindi NON e' una scrittura senza gate: il gate e' chiamato esplicitamente nel
server su entrambe. Il commento a 9478 lo dice a parole sue — «Ora passa per lo
STESSO run_validation_gate, simmetrico a hippo_remember».

⚠️ MA IL CODICE LETTO NON E' UNA MISURA. Questo file esegue le due vie dalla
PORTA (`server.request_handlers[CallToolRequest]`, non la funzione privata) con
una fonte che NON sostiene la proposizione, e guarda cosa arriva nello store.

⚠️ CONTROLLO POSITIVO OBBLIGATORIO, ed e' quello che rende leggibile un rosso:
la stessa via, con una fonte che SOSTIENE la proposizione, deve ammettere. Se
casca quello, il banco non sta misurando il gate — sta misurando che la porta
rifiuta tutto, che e' un'altra cosa e non prova niente.

⚠️ `HIPPO_ENCODE_DELEGATE_ONLY` va TOLTA dall'ambiente prima di lanciare
(`env -u HIPPO_ENCODE_DELEGATE_ONLY python -m pytest ...`): con quella accesa la
delega puo' lasciare passare scritture non giudicate, e il banco misurerebbe la
variabile invece del gate. `main()` la mette con `setdefault` su ogni processo
server, quindi si eredita senza accorgersene.

⛔ Store in tempdir. Nessuna scrittura sullo store del prodotto.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from verimem import mcp_server  # noqa: E402

#: La fonte parla di un ARGOMENTO diverso: non contraddice, semplicemente non
#: sostiene. E' il caso piu' onesto da chiedere a un moat di entailment.
FONTE_CHE_NON_SOSTIENE = (
    "Il verbale del 3 marzo registra che il portone del magazzino B e' stato "
    "ridipinto e che la serratura elettronica e' stata sostituita in giornata."
)
PROPOSIZIONE_NON_SOSTENUTA = "Il tornello 42 risulta aperto da 19 giorni."

#: E qui la fonte dice ESATTAMENTE la proposizione: il controllo positivo.
FONTE_CHE_SOSTIENE = (
    "Verbale di prova del 7 settembre: il tornello 42 risulta aperto da 19 "
    "giorni, come da registro degli accessi."
)
PROPOSIZIONE_SOSTENUTA = "Il tornello 42 risulta aperto da 19 giorni."


@pytest.fixture()
def porta(tmp_path, monkeypatch):
    """Store isolato. Le tre variabili insieme perche' il prodotto ne legge
    piu' d'una a seconda del modulo, e sbagliarne una apre uno SECONDO store
    che sembra vuoto (errore gia' misurato l'08/09 su un altro banco)."""
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(tmp_path))
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    return tmp_path


def _chiama(nome: str, argomenti: dict) -> dict:
    """Passa dalla PORTA, non dall'handler: e' il livello che l'utente digita."""
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=nome, arguments=argomenti))
    r = asyncio.run(handler(req))
    payload = r.root if hasattr(r, "root") else r
    testo = " ".join(c.text for c in payload.content if hasattr(c, "text"))
    try:
        return json.loads(testo)
    except Exception:
        return {"_grezzo": testo}


def _diagnosi(d: dict) -> str:
    """Cosa e' successo, in una riga leggibile dentro l'assert."""
    return (f"ok={d.get('ok')} rejected={d.get('rejected')} "
            f"status={d.get('status')} moat={d.get('moat')} "
            f"grounding={d.get('grounding_score')} reason={d.get('reason')}")


def test_CONTROLLO_una_fonte_che_sostiene_viene_ammessa(porta):
    """Se questo cade, il rosso degli altri due non parla del gate."""
    d = _chiama("hippo_remember", {
        "proposition": PROPOSIZIONE_SOSTENUTA,
        "topic": "banco/ws2/controllo-positivo",
        "source": FONTE_CHE_SOSTIENE,
    })
    assert d.get("ok") is True and not d.get("rejected"), (
        "la porta rifiuta anche una fonte che sostiene la proposizione: questo "
        f"banco non misura il gate. {_diagnosi(d)}")


def test_via_A_hippo_remember_non_ammette_come_verificato_cio_che_la_fonte_non_dice(porta):
    """VIA A: `hippo_remember` con una fonte che parla d'altro.

    Non pretendo il rifiuto: il prodotto ha tre esiti leciti — reject,
    downgrade a `quarantined`, oppure ammissione come `model_claim` NON
    verificato. Quello che NON deve succedere e' che esca un fatto presentato
    come sostenuto dalla fonte: cioe' `grounding_score` alto o status che lo
    faccia sembrare verificato.
    """
    d = _chiama("hippo_remember", {
        "proposition": PROPOSIZIONE_NON_SOSTENUTA,
        "topic": "banco/ws2/fonte-che-non-sostiene",
        "source": FONTE_CHE_NON_SOSTIENE,
    })
    gs = d.get("grounding_score")
    assert d.get("rejected") or d.get("status") == "quarantined" or (
        gs is None or float(gs) < 50.0), (
        "la porta ha ammesso come SOSTENUTA una proposizione che la fonte non "
        f"dice, e senza abbassare la fiducia. {_diagnosi(d)}")


def test_via_B_i_key_facts_dell_episodio_passano_dallo_stesso_gate(porta):
    """VIA B: i `key_facts` di `hippo_record_episode`.

    E' la via che il codice a 9478 dichiara «simmetrica a hippo_remember».
    Qui si misura se lo e' davvero: stessa fonte che non sostiene, stessa
    proposizione, altra porta.
    """
    #: `task_text` e `final_answer`, non `task`: sono i nomi che la porta
    #: pretende (9368-9375, «empty task_text» / «empty final_answer»), e
    #: sbagliarli fa fallire la VALIDAZIONE prima del gate — cioe' un rosso che
    #: parla del banco e non del prodotto. Ci sono cascato al primo giro.
    d = _chiama("hippo_record_episode", {
        "task_text": "banco ws2: una fonte che non sostiene, per la via B",
        "outcome": "success",
        "final_answer": "registrato per il banco",
        "key_facts": [{
            "proposition": PROPOSIZIONE_NON_SOSTENUTA,
            "topic": "banco/ws2/via-b",
            "source": FONTE_CHE_NON_SOSTIENE,
        }],
    })
    esiti = d.get("key_facts") or d.get("key_facts_outcome") or []
    assert esiti, (
        "la ricevuta dell'episodio non dice NIENTE dei key_facts: senza quel "
        f"campo un chiamante non sa se il fatto e' entrato. ricevuta={d}")
    e = esiti[0]
    assert e.get("status") in ("rejected", "quarantined") or (
        "not run" not in str(e.get("moat", ""))), (
        "il key_fact e' entrato senza che il moat abbia giudicato la fonte, e "
        f"la ricevuta non lo segnala come fermato. esito={e}")
