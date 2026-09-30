"""Ogni percorso con cui MCP scrive un fatto deve attaccargli l'etichetta del gate.

PERCHÉ QUESTO FILE ESISTE. Misurato sul corpus il 2026-08-15, contando i fatti
per famiglia di ``writer_principal``::

    cli:*    4011 fatti  ->     0 senza confidence_tier
    sdk:*       7 fatti  ->     0 senza
    mcp:*     145 fatti  ->   145 senza          <- tutti e soli

Non era un ramo che sbagliava il calcolo. ``mcp_server._build_fact`` costruiva
il ``Fact`` **dentro il server**, non passava da ``client.add()``, e il campo
restava ``None`` **per costruzione**. I due esemplari che l'hanno fatta notare
avevano punteggi agli antipodi — **0,19** e **99,95** — e lo stesso esito: la
prova che l'etichetta non dipendeva dalla qualità del fatto ma dalla PORTA da
cui entrava.

⚠️ E IL PRECEDENTE ERA NELLO STESSO PUNTO. Qualcuno aveva già fatto lo stesso
ragionamento per ``writer_principal`` e aveva curato entrambi i chiamanti:
**l'etichetta è stata dimenticata esattamente dove il principal era stato
ricordato**. Per questo il presidio di allora contava le chiamate a
``_build_fact`` invece di provarne una.

🔑 DAL 26/09 (1b.3) QUELLA CLASSE NON PUÒ PIÙ NASCERE QUI. Il server non
costruisce più il fatto: scrive ``Memory.add()``, che calcola l'etichetta per
ogni porta, e ``_build_fact`` non esiste più. Il presidio che contava le sue
chiamate resterebbe verde per assenza — zero chiamate, zero casi, nessun rosso
possibile — e un sensore scollegato è peggio di nessun sensore. La sorveglianza
di «nessuno costruisce un fatto fuori dalla porta» sta ora in
``test_un_fatto_nasce_solo_dalla_porta.py``, per oggetto; QUI resta la promessa
per chi usa il prodotto, misurata alla porta come la chiama un client: il fatto
scritto da ciascuna delle due vie MCP porta l'etichetta nel database.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

TOPIC = "prova/etichetta"
FRASE = "Il deposito di Parma apre alle 7 il lunedì."


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return deposito


def _mcp(nome: str, argomenti: dict) -> dict:
    from verimem.mcp_server import call_tool

    risposta = asyncio.run(call_tool(nome, argomenti))
    return json.loads(risposta[0].text) if risposta else {}


def _etichetta_nel_database(fid: str) -> str | None:
    from verimem.mcp_server import _ag

    percorso = str(_ag().semantic.db_path)
    with sqlite3.connect(f"file:{percorso}?mode=ro", uri=True) as conn:
        riga = conn.execute("SELECT confidence_tier FROM facts WHERE id = ?",
                            (fid,)).fetchone()
    assert riga is not None, f"il fatto {fid} non e' nel database"
    return riga[0]


def test_hippo_remember_scrive_il_fatto_con_l_etichetta(store) -> None:
    r = _mcp("hippo_remember", {"proposition": FRASE, "topic": TOPIC})
    fid = r.get("id")
    assert fid, f"la scrittura non ha reso un id: {r}"
    assert _etichetta_nel_database(fid), (
        "il fatto scritto da hippo_remember non porta confidence_tier: e' il "
        "difetto misurato il 2026-08-15 su 145 fatti su 145")


def test_un_key_fact_scrive_il_fatto_con_l_etichetta(store) -> None:
    r = _mcp("hippo_record_episode", {
        "task_text": "Controllo degli orari del deposito",
        "final_answer": "Orari confermati.",
        "key_facts": [{"proposition": FRASE, "topic": TOPIC}],
    })
    esiti = r.get("key_facts_outcome") or []
    assert esiti and esiti[0].get("id"), f"il key fact non e' stato scritto: {r}"
    assert _etichetta_nel_database(esiti[0]["id"]), (
        "il fatto scritto da key_facts non porta confidence_tier: la seconda "
        "via MCP, quella dove l'etichetta era stata dimenticata")
