"""MCP hippo_remember espone valid_until (v10 valid-time, 2026-06-14).

Lo step 4 (colonna + filtro hard-expire) e' coperto end-to-end da
tests/test_valid_time.py. Qui si verifica il plumbing MCP: l'handler
``hippo_remember`` legge ``valid_until`` dagli arguments e il fatto scritto lo
porta.

🔑 DAL 26/09 (1b.3) SI MISURA NEL DATABASE, non su una spia. Il file faceva da
spia su ``mcp_server._build_fact`` per isolare l'inoltro: ma la fabbrica non
esiste piu', perche' il server scrive con ``Memory.add()``, e una spia su
cio' che la porta non chiama resterebbe muta. Si chiede alla riga scritta.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any

from verimem import mcp_server
from verimem.semantic import SemanticMemory


class _Agent:
    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


async def _invoke(name: str, arguments: dict[str, Any]):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


def _valid_until_scritto(sm: SemanticMemory, testo: str):
    with sqlite3.connect(f"file:{sm.db_path}?mode=ro", uri=True) as conn:
        righe = conn.execute("SELECT valid_until FROM facts WHERE proposition = ?",
                             (testo,)).fetchall()
    assert len(righe) == 1, f"attesa una riga per {testo!r}, trovate {len(righe)}"
    return righe[0][0]


def test_il_motore_scrive_valid_until(tmp_path):
    """Il motore: il param valid_until finisce nel fatto (default None)."""
    from verimem.client import Memory

    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    m = Memory(semantic=sm)
    vu = 1_234_567.0
    m.add("Il listino vale fino al rinnovo.", topic="t", valid_until=vu)
    m.add("Il listino e' pubblicato online.", topic="t")
    assert _valid_until_scritto(sm, "Il listino vale fino al rinnovo.") == vu
    assert _valid_until_scritto(sm, "Il listino e' pubblicato online.") is None


async def test_hippo_remember_forwards_valid_until(tmp_path, monkeypatch):
    """L'handler MCP inoltra valid_until (epoch) e la riga lo porta."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agent(sm))

    vu = time.time() + 86400.0
    await _invoke("hippo_remember", {
        "proposition": "the deploy alpha is in progress",
        "topic": "t/ops",
        "valid_until": vu,
    })
    assert _valid_until_scritto(sm, "the deploy alpha is in progress") == vu, \
        "l'handler MCP deve inoltrare valid_until fino al fatto scritto"


async def test_hippo_remember_absent_valid_until_is_none(tmp_path, monkeypatch):
    """Nessun valid_until negli arguments -> None (nessuna scadenza)."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agent(sm))

    await _invoke("hippo_remember", {"proposition": "stable fact", "topic": "t"})
    assert _valid_until_scritto(sm, "stable fact") is None, \
        "valid_until assente deve diventare None"


async def test_hippo_remember_malformed_valid_until_is_refused_and_says_why(
        tmp_path, monkeypatch):
    """Un valid_until non numerico lo rifiuta lo schema pubblicato, PRIMA del
    gestore: niente crash, niente riga, e l'errore nomina il valore.

    ⚠️ La cella di prima («coercion fail-soft -> None») passava perche' la
    spia sulla fabbrica non veniva MAI chiamata: lo schema rifiutava la
    chiamata e `captured.get(...)` restava None. Verde per assenza — un
    sensore scollegato. Si chiede ora cio' che succede davvero.
    """
    import sqlite3

    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agent(sm))

    blocchi = await _invoke("hippo_remember", {
        "proposition": "x", "topic": "t", "valid_until": "not-a-number",
    })
    # Il rifiuto dello schema torna come testo d'errore, non come JSON.
    testo = " ".join(blocchi)
    assert "not-a-number" in testo, testo
    with sqlite3.connect(f"file:{sm.db_path}?mode=ro", uri=True) as conn:
        n = conn.execute("SELECT COUNT(*) FROM facts WHERE proposition = 'x'").fetchone()[0]
    assert n == 0, "rifiutata e scritta lo stesso"
