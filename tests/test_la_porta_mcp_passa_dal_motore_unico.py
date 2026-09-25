"""1b.3 — la porta MCP scrive passando da `Memory.add()`: cio' che vale ORA.

D-0013: **motore unico**. Le vie che creano un `Fact` dalla porta MCP sono TRE
— `hippo_document_promote_chunk` (218 righe, curata qui), `hippo_record_episode`
(296) e `hippo_remember` (888) — e nessuna passava da `add()`, dove vive il
traduttore della ricevuta.

⚠️ QUESTO BANCO TIENE SOLO CIO' CHE QUESTA RICHIESTA CURA. Le celle delle due
vie ancora da fare **non stanno qui**: un rosso che nessuno ha promesso di
spegnere in questa richiesta non e' un guardiano, e' rumore che insegna a
convivere col rosso — e un `xfail` sarebbe peggio, perche' spegne il segnale
invece di toglierlo. Quelle misure vivono nella nota (`ws2-1b3-la-porta-mcp.md`,
punto 7-ter) col numero di righe di ciascuna, e tornano qui insieme alla loro
cura.

La promozione di un chunk ha il suo banco:
`test_la_promozione_di_un_chunk_passa_dal_motore_unico.py`.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

TOPIC = "prova/1b3"
FRASE = "Il totale della fattura e' 500 euro."


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return deposito


def _chiama(nome: str, argomenti: dict) -> dict:
    from verimem.mcp_server import call_tool

    risposta = asyncio.run(call_tool(nome, argomenti))
    return json.loads(risposta[0].text) if risposta else {}


def test_la_stessa_frase_due_volte_resta_UN_fatto(store):
    """T162: l'id deriva dal contenuto, e la seconda scrittura lo dichiara.

    E' la proprieta' che il motore unico deve **preservare**, non introdurre:
    oggi vale su MCP (stesso id, `replaced` da False a True) e non sull'SDK,
    dove la stessa frase scritta due volte fa due fatti. La cella sta qui
    perche' e' qui che oggi e' vera: se una cura la rompesse, porterebbe la
    duplicazione dell'SDK dentro l'unica porta che non ce l'ha.
    """
    primo = _chiama("hippo_remember", {"proposition": FRASE, "topic": TOPIC})
    secondo = _chiama("hippo_remember", {"proposition": FRASE, "topic": TOPIC})

    assert primo.get("id") == secondo.get("id"), (
        f"due id per la stessa frase: {primo.get('id')} / {secondo.get('id')}")
    assert secondo.get("replaced") is True, (
        "la seconda scrittura non dichiara di aver sostituito la riga")
