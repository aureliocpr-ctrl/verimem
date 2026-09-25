"""1b.3 — la promozione di un chunk passa dal motore unico.

`hippo_document_promote_chunk` e' la piu' piccola delle tre vie che creano un
`Fact` dalla porta MCP (218 righe in un modulo suo, contro le 296 di
`hippo_record_episode` e le 888 di `hippo_remember`), e fa lo stesso difetto:
costruisce il `Fact` a mano (`document_promote.py:215`) e lo persiste con
`semantic_memory.store()` **senza passare da `Memory.add()`** — dove vive il
traduttore della ricevuta. Per questo la sua ricevuta non ha i nomi del nucleo.

⚠️ QUESTO BANCO MISURA LA PORTA, non la funzione: chiama il tool come lo chiama
un client. Il livello a cui si misura decide il verdetto, e la funzione puo'
essere giusta mentre la porta non la usa — e' gia' successo tre volte.

⚠️ E LA PRIMA CELLA NON E' SUL COMPORTAMENTO, E' SUI PERCORSI. `Memory(path)`
vuole il FILE del database, non la cartella: con un percorso di file sbagliato
non si ottiene un errore, si apre **un secondo store vuoto** — misurato il
20/09 da due strade diverse (`OperationalError` passando la cartella, e
`facts list --db` su un percorso inesistente che esce `EXIT=0` creando un file
di 73728 byte). Se i due `db_path` non coincidono, ogni verde successivo di
questo banco sarebbe preso su due file che non si parlano.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from verimem.core import CHIAVI

TOPIC = "prova/1b3-chunk"
TESTO = "Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo."


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return deposito


def _promuovi(**extra) -> dict:
    """Chiama il tool come lo chiama un client, e rende la ricevuta."""
    from verimem.mcp_server import call_tool

    #: ⚠️ I CAMPI VERI DELLO SCHEMA, non quelli che credevo: `required` e'
    #: `['text','source_id','start','end']`. Chiamando con `content` il tool
    #: NON rifiuta — scrive un fatto con `proposition='None'` e
    #: `citation='file:None:None-None'`. Quello e' un difetto suo, aperto a
    #: parte; qui si misura la promozione VERA, con gli argomenti giusti.
    argomenti = {"text": TESTO, "source_id": "doc-collaudo",
                 "start": 0, "end": len(TESTO), "topic": TOPIC}
    argomenti.update(extra)
    risposta = asyncio.run(call_tool("hippo_document_promote_chunk", argomenti))
    r = json.loads(risposta[0].text) if risposta else {}
    #: `error` C'E' SEMPRE e vale `None` quando va bene: si guarda il VALORE.
    assert not r.get("error"), f"la chiamata non e' partita: {r}"
    return r


def test_i_due_db_path_coincidono(store):
    """La cella che viene prima di tutte: un solo file, non due.

    Il server terra' una `Memory` process-wide; se non guarda lo stesso file
    dell'agent, la promozione scriverebbe in uno store e la lettura andrebbe
    nell'altro — e il banco direbbe «non trovato» per la ragione sbagliata.
    """
    from verimem.client import Memory
    from verimem.mcp_server import _ag

    via_agent = str(getattr(getattr(_ag(), "semantic", None), "db_path", ""))
    assert via_agent, "l'agent non dichiara il suo db_path"
    via_client = str(getattr(getattr(Memory(via_agent), "semantic", None),
                             "db_path", ""))
    assert (os.path.normcase(os.path.abspath(via_agent))
            == os.path.normcase(os.path.abspath(via_client))), (
        f"due store invece di uno:\n  agent : {via_agent}\n  client: {via_client}")


def test_il_fatto_promosso_porta_il_writer_principal(store):
    """Chi ha scritto, detto dal fatto che sta nello store.

    `_MCP_PRINCIPAL` esiste apposta — «separa chi ha scritto via MCP da
    sdk/gateway writes» — e le altre due vie lo timbrano. Questa no: il suo
    `Fact` viene costruito a mano senza quel campo, quindi una promozione e'
    indistinguibile da una scrittura interna.
    """
    from verimem.mcp_server import _ag

    r = _promuovi()
    ident = str(r.get("fact_id") or r.get("id") or "")
    assert ident, f"nessun fatto promosso: {r}"
    fatto = _ag().semantic.get(ident)
    assert fatto is not None, f"il fatto {ident} non si rilegge dallo store"
    #: ⚠️ NON basta «non vuoto», e l'ho imparato falsificando: `add()` usa
    #: `principal or self._principal`, quindi il campo resta pieno anche se la
    #: porta non passa il suo timbro — spegnendo la cura il banco restava
    #: verde. Un controllo che accetta il DEFAULT non misura la cura: misura
    #: che esista un valore. Qui si pretende il timbro di QUESTA porta.
    from verimem.mcp_server import _MCP_PRINCIPAL

    assert getattr(fatto, "writer_principal", None) == _MCP_PRINCIPAL, (
        "il fatto promosso non porta il timbro della porta MCP: "
        f"writer_principal={getattr(fatto, 'writer_principal', None)!r} "
        f"invece di {_MCP_PRINCIPAL!r}")


def test_il_fatto_promosso_porta_la_provenienza(store):
    """`source_signature` e' l'unico campo di provenienza che sopravvive.

    `add()` la calcola da se' (`client.py:906`); questa via non ci passa, e la
    citazione del documento resta solo in `verified_by`/`source_episodes`.
    """
    from verimem.mcp_server import _ag

    r = _promuovi()
    ident = str(r.get("fact_id") or r.get("id") or "")
    fatto = _ag().semantic.get(ident)
    assert getattr(fatto, "source_signature", None), (
        "il fatto promosso non porta l'impronta della fonte")


def test_la_ricevuta_della_promozione_rende_le_chiavi_del_nucleo(store):
    """14/14, come le altre porte.

    Oggi la risposta ha un suo schema (`stored`, `fact_id`, `citation`,
    `grounding_note`, `trattenuto_da`): chi legge una promozione non trova
    nessuno dei nomi che trova altrove.
    """
    r = _promuovi()
    mancanti = sorted(set(CHIAVI) - set(r))
    assert not mancanti, f"la promozione non rende: {mancanti}"
