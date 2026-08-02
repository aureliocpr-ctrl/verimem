"""Il canale MCP prometteva la cancellazione GDPR e non toglieva la catena.

Il commit precedente ha aperto `--purge-history` sulla riga di comando e ha
lasciato fuori l'MCP — trovato dall'altra istanza contando le occorrenze:
`purge_history` compare 6 volte in `cli.py`, 3 in `client.py`, 2 in
`gateway.py` e **0 in `mcp_server.py`**. Cioe' esattamente lo sweep mancato
che quel commit descriveva come classe.

E non bastava aggiungere una chiave all'inputSchema: `hippo_fact_forget`
chiamava `a.semantic.delete(fid, principal=…, action=…)`, e la firma di quel
metodo e' `['fact_id', 'principal', 'action']` — il parametro NON ESISTE su
quel livello. La cancellazione con catena vive su `Memory.delete`, che sta uno
strato piu' su. Andava cambiata la catena delle chiamate, non lo schema.

Il tool si descrive «Delete one fact by id (privacy / GDPR)», ed e' il canale
che usano gli agenti: la promessa piu' esposta era quella scoperta.
"""
from __future__ import annotations

import asyncio
import sqlite3

import pytest

SEGRETO = "Il codice fiscale del cliente e RSSMRA80A01H501U."


def _chiama(nome: str, args: dict):
    from verimem import mcp_server as srv
    return asyncio.run(srv.call_tool(nome, args))


@pytest.fixture()
def store_con_catena(tmp_path, monkeypatch):
    from verimem import mcp_server as srv
    from verimem.client import Memory

    m = Memory(path=tmp_path / "m.db")
    vecchio = m.add(SEGRETO, topic="pii")["id"]
    nuovo = m.update(vecchio, SEGRETO + " Verificato.")["id"]

    class _Ag:
        def __init__(self, mem):
            self.semantic = mem.semantic
    monkeypatch.setattr(srv, "_ag", lambda: _Ag(m))
    return m, vecchio, nuovo


def _righe_col_segreto(m) -> int:
    con = sqlite3.connect(m.semantic.db_path)
    try:
        return con.execute(
            "SELECT COUNT(*) FROM facts WHERE proposition LIKE '%RSSMRA%'"
        ).fetchone()[0]
    finally:
        con.close()


def test_il_tool_accetta_purge_history(store_con_catena):
    m, _vecchio, nuovo = store_con_catena
    _chiama("hippo_fact_forget", {"fact_id": nuovo, "purge_history": True})
    assert _righe_col_segreto(m) == 0, (
        "il dato sensibile e' ancora nel database dopo una cancellazione "
        "chiesta con purge_history dal canale che gli agenti usano")


def test_senza_il_flag_il_comportamento_non_cambia(store_con_catena):
    """Il default resta quello di prima: si toglie una riga e la catena
    rimane. Cambiarlo in silenzio distruggerebbe provenienza a chi non l'ha
    chiesto."""
    m, _vecchio, nuovo = store_con_catena
    _chiama("hippo_fact_forget", {"fact_id": nuovo})
    assert _righe_col_segreto(m) == 1


def test_lo_schema_del_tool_lo_dichiara():
    """Un parametro che il tool accetta e non annuncia non esiste per un
    agente: lo schema E' la documentazione su questo canale."""
    from verimem import mcp_server as srv

    tools = asyncio.run(srv.list_tools())
    forget = next(t for t in tools if t.name == "hippo_fact_forget")
    assert "purge_history" in (forget.inputSchema.get("properties") or {}), (
        f"non dichiarato: {sorted(forget.inputSchema.get('properties') or {})}")
    assert "purge" in (forget.description or "").lower(), forget.description
