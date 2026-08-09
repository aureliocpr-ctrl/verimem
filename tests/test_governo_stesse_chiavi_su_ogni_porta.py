"""Le porte del governo dicono le stesse cose con gli stessi nomi.

Misurato da ws5 il 2026-08-05 su un'altra superficie: `recall` chiama quel
campo ``text`` ed `explain` lo chiama ``proposition`` — due nomi per la
stessa cosa, e gli è quasi costato un referto sbagliato («explain sbaglia 10
su 10», mentre era corretto). È la classe «due implementazioni divergenti
dello stesso gesto» vista dal lato dei NOMI.

Il governo non ce l'ha, e non per fortuna: SDK, CLI, MCP e HTTP chiamano
tutti `verimem.retirement_log`, non reimplementano la query. Questo test
pinna quella proprietà, così il giorno in cui qualcuno duplica la logica in
una porta «per comodità» il banco lo prende subito — che è l'unico momento
in cui costa poco correggerlo.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_log as _rl
from verimem.retirement_log import survivability_counts as _sc


@pytest.fixture()
def con_un_ritiro(tmp_path):
    m = Memory(tmp_path / "memory.db")
    a = m.add("Il server nexus ha 64 gigabyte di RAM.", topic="t/a",
              verified_by=["doc"])["id"]
    b = m.add("Il magazzino K-77 ha 4200 metri quadri.", topic="t/b",
              verified_by=["doc"])["id"]
    m.semantic.supersede(a, b, principal="test:chiavi", reason="banco")
    return m


def _mcp_items(m, tool: str, args: dict):
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    class _A:
        def __init__(self) -> None:
            self.semantic = m.semantic

    orig = mcp_server._ag
    mcp_server._ag = lambda: _A()
    try:
        async def call():
            h = mcp_server.server.request_handlers[CallToolRequest]
            r = await h(CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(name=tool, arguments=args)))
            p = r.root if hasattr(r, "root") else r
            return json.loads(next(c.text for c in p.content
                                   if hasattr(c, "text")))
        return asyncio.run(call())
    finally:
        mcp_server._ag = orig


def test_le_righe_del_retirement_log_hanno_le_stesse_chiavi(con_un_ritiro):
    m = con_un_ritiro
    sdk = set(m.retirement_log(limit=1)[0].keys())
    modulo = set(_rl(m.semantic, limit=1)[0].keys())   # ciò che usano CLI e HTTP
    mcp = set(_mcp_items(m, "hippo_retirement_log", {"limit": 1})["items"][0])
    assert sdk == modulo == mcp, {"sdk": sorted(sdk), "modulo": sorted(modulo),
                                  "mcp": sorted(mcp)}


def test_il_quartetto_ha_le_stesse_chiavi(con_un_ritiro):
    m = con_un_ritiro
    sdk = set(m.survivability().keys())
    modulo = set(_sc(m.semantic).keys())
    mcp = _mcp_items(m, "hippo_retirement_log", {"counts": True})
    mcp_keys = {k for k in mcp if k != "ok"}
    assert sdk == modulo, {"sdk": sorted(sdk), "modulo": sorted(modulo)}
    assert sdk <= mcp_keys, {"sdk": sorted(sdk), "mcp": sorted(mcp_keys)}


def test_la_formula_viaggia_su_ogni_porta(con_un_ritiro):
    """Il numero senza la sua definizione è il difetto che questo ramo cura:
    `formula` non è decorazione, è il contratto del contatore."""
    m = con_un_ritiro
    assert "servable =" in m.survivability()["formula"]
    assert "servable =" in _sc(m.semantic)["formula"]
    assert "servable =" in _mcp_items(
        m, "hippo_retirement_log", {"counts": True})["formula"]
