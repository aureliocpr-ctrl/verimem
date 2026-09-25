"""T184 — una chiamata che viola lo schema non scrive un fatto inventato.

IL DIFETTO, misurato alla porta il 20/09: `hippo_document_promote_chunk`
dichiara `required: ['text','source_id','start','end']` e accetta una chiamata
che non ne ha nessuno. Non rifiuta: **scrive**.

    {"stored": true, "fact_id": "1fad29b39503",
     "citation": "file:None:None-None", "error": null, "status": "model_claim"}
    fatto riletto dallo store -> proposition = 'None'

Un fatto la cui proposizione e' la stringa `'None'`, `model_claim`, quindi
servibile nel recall come qualunque altro. Non e' un fatto perso: e' un fatto
**inventato dal prodotto**, perche' nessuno ha detto no a una chiamata monca.

LA CAUSA, misurata e non dedotta: `_validate_input` usa
`_SCHEMAS_BY_TOOL.get(name) or _DERIVED_SCHEMAS.get(name)`. I manuali sono 11 e
non comprendono ne' `hippo_remember` ne' questa via; i derivati (215, popolati
alla prima chiamata) portano «type/enum only, **no required**». Percio'
`remember` rifiuta un `writer_role` fuori enum — l'enum il derivato ce l'ha —
mentre qui i quattro obbligatori non vengono guardati. **Lo schema che il
client legge da `list_tools()` non e' quello con cui la porta valida.**

⚠️ E LO STORE SI LEGGE DAL DATABASE, NON DALLA RISPOSTA. «ha risposto errore» e
«non ha scritto» sono due cose diverse, e qui conta la seconda: una porta che
dice no e scrive lo stesso e' peggio di una che dice si'.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

TOPIC = "prova/t184"
TESTO = "Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo."


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return deposito


def _chiama(argomenti: dict) -> dict:
    from verimem.mcp_server import call_tool

    risposta = asyncio.run(call_tool("hippo_document_promote_chunk", argomenti))
    return json.loads(risposta[0].text) if risposta else {}


def _fatti_nel_database() -> int:
    """Conta SUL DATABASE: la risposta racconta, la tabella testimonia."""
    from verimem.mcp_server import _ag

    percorso = str(_ag().semantic.db_path)
    with sqlite3.connect(f"file:{percorso}?mode=ro", uri=True) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0])


def test_una_chiamata_senza_i_campi_obbligatori_viene_RIFIUTATA(store):
    prima = _fatti_nel_database()
    r = _chiama({"content": "Un testo qualunque.", "topic": TOPIC})

    assert r.get("stored") is False, f"la chiamata monca ha scritto: {r}"
    assert r.get("error"), "rifiutata senza dire perche'"


def test_e_soprattutto_NON_SCRIVE_niente_nello_store(store):
    """La cella che conta: lo stato del database, non il testo della risposta.

    Una porta puo' rispondere «errore» e aver gia' scritto — ed e' il caso
    peggiore, perche' chi legge la risposta smette di cercare.
    """
    prima = _fatti_nel_database()
    _chiama({"content": "Un testo qualunque.", "topic": TOPIC})
    dopo = _fatti_nel_database()

    assert dopo == prima, (
        f"lo store e' cambiato dopo una chiamata rifiutata: {prima} -> {dopo}")


def test_l_errore_NOMINA_i_campi_che_mancano(store):
    """Un «non valido» che non dice quale campo manca fa ripetere il tentativo.

    Lo schema li conosce: `required` sta li'. Tacerli e' una scelta, ed e'
    quella che costa un giro a chi chiama.
    """
    r = _chiama({"content": "Un testo qualunque.", "topic": TOPIC})
    testo = str(r.get("error") or "").lower()
    assert "text" in testo, f"l'errore non nomina i campi mancanti: {r.get('error')!r}"


def test_IL_CONTROLLO_POSITIVO_la_chiamata_corretta_scrive_come_prima(store):
    """Senza questo, il rosso si spegne rompendo la porta invece di curarla."""
    prima = _fatti_nel_database()
    r = _chiama({"text": TESTO, "source_id": "doc-collaudo", "start": 0,
                 "end": len(TESTO), "topic": TOPIC})

    assert not r.get("error"), f"la chiamata VALIDA e' stata rifiutata: {r}"
    assert r.get("stored") is True, f"la chiamata valida non ha scritto: {r}"
    assert _fatti_nel_database() == prima + 1, "il fatto valido non e' nel database"


def test_ogni_tool_che_dichiara_required_lo_FA_RISPETTARE(store):
    """La condizione che vale per tutti: il contratto pubblicato è applicato.

    ⚠️ QUESTA CELLA E' STATA RISCRITTA, e il perché conta più del numero. La
    prima versione contava i campi letti come `arguments.get("x", "")` — i
    **ripieghi** — e ne trovava 130, fra cui `hippo_recall.query`. Da lì avevo
    concluso che «`required` non è applicato nemmeno dove lo schema è scritto
    a mano». **Falso**, e la porta lo dice in due righe:

        hippo_recall senza query -> "schema violation: 'query' is a required property"

    Quel ripiego è **codice morto** dietro una validazione che funziona.
    Contavo la FORMA del sorgente invece di chiedere alla porta cosa fa: il
    righello descriveva la forma, non l'oggetto. Ora si misura il
    comportamento — e un ripiego dietro una validazione attiva è innocuo.

    Numero misurato il 20/09: **123** tool pubblicano `required`, **9** lo
    fanno rispettare (esattamente quelli con schema scritto a mano), **114**
    no.
    """
    from verimem.mcp_server import _validate_input, list_tools

    non_applicano = []
    for s in asyncio.run(list_tools()):
        richiesti = (getattr(s, "inputSchema", {}) or {}).get("required") or []
        if richiesti and not _validate_input(s.name, {}):
            non_applicano.append(f"{s.name}({','.join(richiesti)})")

    assert not non_applicano, (
        f"{len(non_applicano)} tool dichiarano campi obbligatori e accettano "
        f"lo stesso una chiamata vuota: {non_applicano[:6]}…")
