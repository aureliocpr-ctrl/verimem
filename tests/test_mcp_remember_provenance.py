"""Cycle #109 S2 — MCP hippo_remember accepts provenance fields.

Pattern ProvSEEK 2508.21323: ogni claim LLM deve mappare a row_id
verificabile. ``hippo_remember`` accetta ``verified_by`` e ``status``;
default ``status='model_claim'`` per backward compat.

🔑 DAL 26/09 (1b.3) SI MISURA ALLA PORTA, non sulla fabbrica. Questo file
provava ``mcp_server._build_fact`` e poi chiamava ``SemanticMemory.store`` a
mano: provava due pezzi che la porta non usa piu', perche' il server scrive
con ``Memory.add()`` come ogni altra porta. Le stesse promesse si chiedono ora
a ``call_tool("hippo_remember", ...)``, su uno store usa-e-getta.

⚠️ E UNA PROMESSA CAMBIA DI PROPOSITO: ``source_signature`` passata dal client
non entra piu' nel fatto. Una firma senza la fonte faceva passare due misure
per «due fonti distinte»; la firma la calcola solo il motore, dalla fonte, e
l'argomento si ignora dichiarandolo (cella in
``test_la_stessa_scrittura_da_ogni_porta.py``).
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return deposito


def _ricorda(**argomenti) -> dict:
    from verimem.mcp_server import call_tool

    risposta = asyncio.run(call_tool("hippo_remember", argomenti))
    return json.loads(risposta[0].text) if risposta else {}


def _riga(fid: str) -> dict:
    from verimem.mcp_server import _ag

    percorso = str(_ag().semantic.db_path)
    with sqlite3.connect(f"file:{percorso}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        r = conn.execute("SELECT status, verified_by, source_signature "
                         "FROM facts WHERE id = ?", (fid,)).fetchone()
    assert r is not None, f"il fatto {fid} non e' nel database"
    return {"status": r["status"], "verified_by": json.loads(r["verified_by"] or "[]"),
            "source_signature": r["source_signature"]}


def test_verified_by_arriva_nel_fatto(store) -> None:
    r = _ricorda(proposition="Il report settimanale conta 280 righe.",
                 topic="t/prov", verified_by=["bash:cmd", "file:x:1"])
    assert _riga(r["id"])["verified_by"] == ["bash:cmd", "file:x:1"]


def test_verified_senza_riferimenti_verificabili_torna_model_claim(store) -> None:
    """Cycle #111 v2: una traccia storica di comando non e' verificabile per
    I/O, quindi `status='verified'` scende a `model_claim`; il payload resta."""
    r = _ricorda(proposition="Il catalogo del 2025 elenca 17280 articoli.",
                 topic="project/catalogo", confidence=0.95,
                 verified_by=["bash:pytest_collect:exit0:17280"],
                 status="verified")
    riga = _riga(r["id"])
    assert riga["status"] == "model_claim"
    assert riga["verified_by"] == ["bash:pytest_collect:exit0:17280"]


def test_uno_status_inventato_e_rifiutato_e_non_scrive(store) -> None:
    from verimem.mcp_server import _ag

    r = _ricorda(proposition="Il magazzino ha tre piani.", topic="t/prov",
                 status="totally_bogus")
    # Lo rifiuta lo schema pubblicato, prima del motore: l'errore nomina il
    # valore che non e' fra quelli ammessi.
    assert "totally_bogus" in str(r.get("error", "")), f"rifiutato senza dire perche': {r}"
    percorso = str(_ag().semantic.db_path)
    with sqlite3.connect(f"file:{percorso}?mode=ro", uri=True) as conn:
        n = conn.execute("SELECT COUNT(*) FROM facts WHERE proposition = ?",
                         ("Il magazzino ha tre piani.",)).fetchone()[0]
    assert n == 0, "ha risposto con un errore e ha scritto lo stesso"


def test_senza_verified_by_il_fatto_e_model_claim(store) -> None:
    r = _ricorda(proposition="Il bando scade il 30 ottobre.", topic="t/prov",
                 confidence=0.5)
    riga = _riga(r["id"])
    assert riga["status"] == "model_claim"
    assert riga["verified_by"] == []


def test_provisional_con_un_url_resta_provisional(store) -> None:
    r = _ricorda(proposition="Self-RAG outperforms ChatGPT on PopQA 55.8 vs 29.3",
                 topic="research/self-rag-2023", confidence=0.85,
                 verified_by=["url:arxiv.org/abs/2310.11511:tab2"],
                 status="provisional")
    riga = _riga(r["id"])
    assert riga["status"] == "provisional"
    assert riga["verified_by"][0].startswith("url:arxiv")


def test_la_firma_della_fonte_del_client_non_entra(store) -> None:
    r = _ricorda(proposition="Il deposito chiude alle 19.", topic="t/prov",
                 source_signature="cycle109-2026-05-16")
    assert _riga(r["id"])["source_signature"] is None
