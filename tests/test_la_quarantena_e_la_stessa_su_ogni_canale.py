"""`quarantine_log` aveva tre superfici e tre comportamenti.

Il README promette che «the same pair is on the MCP surface». Non reggeva, e
le superfici divergevano in DIREZIONI OPPOSTE:

    SDK      client.py:1443      SELECT + arricchimento reason/layers + explain
    gateway  gateway.py:1308     delega all'SDK (ha l'arricchimento), non passa explain
    MCP      mcp_server.py:13011 ha explain, RIPETE la SELECT, niente arricchimento

Il MCP ricopiava le righe `client.py:1447-1452` invece di chiamare l'SDK, e
con la copia si e' perso cio' che la copia non conteneva: `reason` e `layers`,
cioe' PERCHE' ogni claim e' stato fermato. Sapere quali fatti sono in
quarantena senza sapere perche' non permette di correggerne nessuno — che e'
esattamente la ragione per cui l'arricchimento era stato scritto.

E il commento sopra quel blocco dice di star chiudendo proprio questa classe:
«sta anche qui, e non solo sull'SDK, perche' una capacita' su un canale solo
e' il difetto che questa serie di commit ha passato la giornata a chiudere».
Lo sweep si e' fermato a `explain` e non ha guardato la riga sopra.

C'e' un secondo effetto, piu' fine: `client.py:1505` salta il ricalcolo quando
la riga porta gia' un `reason` («l'audit trail sapeva gia' dirlo»). Su MCP
`reason` non era mai popolato, quindi quell'opt-in ricalcolava tutto e il
risparmio che dichiara non esisteva.

QUARTA GENERAZIONE della stessa classe in un giorno — `7b8af116` (il moat
girava da CLI e non da MCP), `76d5dc1c` (la ricevuta leggeva il verdetto solo
in un verso), `b9688115`/`b620bfd4` (la cancellazione con la catena) — e la
cura e' sempre la stessa: **una superficie sola, e gli altri canali la
chiamano**.
"""
from __future__ import annotations

import asyncio

import pytest

from verimem.client import Memory

CLAIM = "The migration was completed and all tests pass."


@pytest.fixture()
def store_con_quarantena(tmp_path, monkeypatch):
    from verimem import mcp_server as srv

    m = Memory(path=tmp_path / "m.db")
    for i in range(3):
        m.add(f"{CLAIM} Batch {i} shipped and verified.", topic="t")

    class _Ag:
        def __init__(self, mem):
            self.memory = mem
            self.semantic = mem.semantic
    monkeypatch.setattr(srv, "_ag", lambda: _Ag(m))
    return m


def _mcp(args: dict) -> dict:
    import json

    from verimem import mcp_server as srv
    res = asyncio.run(srv.call_tool("hippo_quarantine_log", args))
    return json.loads(res[0].text)


def test_le_chiavi_sono_le_STESSE_su_SDK_e_MCP(store_con_quarantena):
    """Il criterio, non l'elenco: qualunque cosa l'SDK aggiunga a una riga,
    il canale MCP la porta. Se domani nasce un campo nuovo e solo l'SDK lo
    riceve, questo test cade da solo."""
    m = store_con_quarantena
    sdk = m.quarantine_log(limit=50)
    assert sdk, "presupposto: qualcosa in quarantena"
    mcp = _mcp({"limit": 50}).get("quarantined") or []
    assert mcp, "il canale MCP non restituisce nulla"
    assert set(mcp[0]) == set(sdk[0]), (
        f"chiavi diverse\n  SDK: {sorted(sdk[0])}\n  MCP: {sorted(mcp[0])}")


def test_il_canale_MCP_dice_PERCHE_ogni_claim_e_fermo(store_con_quarantena):
    """`reason` e `layers` sono il motivo per cui l'arricchimento esiste:
    senza, un log della quarantena elenca e non spiega."""
    righe = _mcp({"limit": 50}).get("quarantined") or []
    assert righe, "nessuna riga"
    assert "layers" in righe[0], sorted(righe[0])


def test_explain_continua_a_funzionare_su_MCP(store_con_quarantena):
    """Il caso che gia' andava non deve rompersi con la delega."""
    righe = _mcp({"limit": 50, "explain": True}).get("quarantined") or []
    assert righe, "nessuna riga"
    assert any(r.get("reason") or r.get("layers") for r in righe), righe[0]


def test_uno_store_illeggibile_non_fa_esplodere_il_canale(tmp_path, monkeypatch):
    """Il contratto dell'SDK e' «vista in sola lettura: uno store illeggibile
    mostra vuoto, non 500». La delega non deve perderlo."""
    from verimem import mcp_server as srv

    m = Memory(path=tmp_path / "m.db")

    class _Rotto:
        def quarantine_log(self, **kw):
            raise RuntimeError("store giu'")

    class _Ag:
        memory = _Rotto()
        semantic = m.semantic
    monkeypatch.setattr(srv, "_ag", lambda: _Ag())
    out = _mcp({"limit": 10})
    assert out.get("quarantined") == [] or out.get("error"), out
