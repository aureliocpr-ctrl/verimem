"""1b.3 (A) — la porta MCP scrive passando da `Memory.add()`, come le altre due.

D-0013: **motore unico**. Oggi le due vie che creano un Fact da MCP non passano
da `add()`, e per questo la ricevuta del nucleo su quella porta e' 3/14 mentre
CLI e libreria sono a 14/14: il traduttore sta su `add()`, e chi non ci passa
non lo incontra. Curare la ricevuta senza curare la giuntura vorrebbe dire una
terza copia della traduzione — la classe ① che tutta la fetta esiste per
togliere.

⚠️ QUESTO BANCO MISURA LA PROPRIETA', NON L'IMPLEMENTAZIONE. Non chiede «la
riga 13930 e' sparita»: chiede **che la scrittura attraversi `Memory.add()`**.
Se domani il percorso cambia nome, il banco regge; se qualcuno cura la ricevuta
copiando l'adattatore in un terzo punto, il banco resta ROSSO — ed e' giusto,
perche' la copia e' il difetto.

⚠️ E IL PUNTO D'INNESTO VA PRIMA DEL WORKER. L'INSERT di `hippo_remember` parte
da `semantic.py:_work` (`store_within_budget`), cioe' fuori dal filo della
chiamata: innestare dove finisce la scrittura arriverebbe troppo tardi. Lo
stack misurato il 19/09 lo mostra, e per questo la cella conta le chiamate ad
`add()` invece di guardare dove nasce l'INSERT.

NOTA SULLE DUE VIE: sono `hippo_remember` e `hippo_document_promote_chunk`
(`document_promote.py:promote_chunk_to_fact`) — censite per oggetto, con una
sonda sugli INSERT della tabella `facts`, non per nome.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from verimem.core import CHIAVI

TOPIC = "prova/1b3"
FRASE = "Il totale della fattura e' 500 euro."


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return deposito


@pytest.fixture
def conta_add(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Registra OGNI passaggio da `Memory.add`, chiamando l'originale.

    Contare le chiamate e' il modo di chiedere «ci sei passato?» senza legarsi
    a come ci si passa. Il wrapper NON sostituisce il comportamento: lo osserva.
    """
    from verimem.client import Memory

    passaggi: list[dict] = []
    originale = Memory.add

    def spia(self, *args, **kwargs):
        passaggi.append({"args": args, "kwargs": kwargs})
        return originale(self, *args, **kwargs)

    monkeypatch.setattr(Memory, "add", spia)
    return passaggi


def _chiama(nome: str, argomenti: dict) -> dict:
    from verimem.mcp_server import call_tool

    risposta = asyncio.run(call_tool(nome, argomenti))
    return json.loads(risposta[0].text) if risposta else {}


def test_hippo_remember_passa_da_Memory_add(store, conta_add):
    r = _chiama("hippo_remember", {"proposition": FRASE, "topic": TOPIC})
    assert r.get("id"), f"la scrittura non e' avvenuta: {r}"
    assert conta_add, (
        "la porta MCP ha scritto SENZA passare da Memory.add(): il motore "
        "non e' unico e il traduttore della ricevuta non la incontra")


def test_document_promote_chunk_passa_da_Memory_add(store, conta_add):
    """La seconda via, quella che il grafo delle chiamate non vedeva.

    Non ha `proposition` ma `content`, e per questo un censimento fatto sui
    nomi non la trovava: l'ha trovata la selezione per schema, e la sonda sugli
    INSERT ha confermato che scrive un Fact davvero.
    """
    r = _chiama("hippo_document_promote_chunk",
                {"content": FRASE, "topic": TOPIC})
    #: ⚠️ `error` C'E' SEMPRE e vale `None` quando non c'e' errore: chiedere
    #: `"error" not in r` misura la FORMA della risposta, non l'esito. E' lo
    #: stesso inciampo che il prodotto documenta su `replaced` («un campo che
    #: c'e' e vale False si legge diverso da un campo che manca»), rifatto qui.
    assert not r.get("error"), f"la chiamata non e' partita: {r}"
    assert r.get("fact_id") or r.get("id"), f"nessun Fact creato: {r}"
    assert conta_add, (
        "document_promote_chunk crea un Fact senza passare da Memory.add()")


@pytest.mark.parametrize("con_fonte", [False, True])
def test_la_ricevuta_MCP_rende_le_chiavi_del_nucleo(store, con_fonte):
    """14/14, e lo stesso insieme con e senza fonte.

    Il numero non deve dipendere dall'ingresso: sulla CLI, prima della cura,
    erano 11 con la source e 10 senza — un contratto che cambia col comando
    non e' un contratto.
    """
    argomenti = {"proposition": FRASE, "topic": TOPIC}
    if con_fonte:
        argomenti["source"] = "Il documento riporta un totale di 500 euro."
    r = _chiama("hippo_remember", argomenti)
    mancanti = sorted(set(CHIAVI) - set(r))
    assert not mancanti, f"la porta MCP non rende: {mancanti}"


def test_la_stessa_frase_due_volte_resta_UN_fatto(store):
    """T162: l'id deriva dal contenuto, e la seconda scrittura lo dice.

    E' la proprieta' che il motore unico deve PRESERVARE, non introdurre: oggi
    vale su MCP (stesso id, `replaced` da False a True) e non sull'SDK. La
    cella sta qui perche' e' qui che oggi e' vera: se la cura la rompesse,
    porterebbe la duplicazione dell'SDK dentro l'unica porta che non ce l'ha.
    """
    primo = _chiama("hippo_remember", {"proposition": FRASE, "topic": TOPIC})
    secondo = _chiama("hippo_remember", {"proposition": FRASE, "topic": TOPIC})
    assert primo.get("id") == secondo.get("id"), (
        f"due id per la stessa frase: {primo.get('id')} / {secondo.get('id')}")
    assert secondo.get("replaced") is True, (
        "la seconda scrittura non dichiara di aver sostituito la riga")
