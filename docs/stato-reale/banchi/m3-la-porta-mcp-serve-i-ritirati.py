"""M3 — la porta MCP restituisce un fatto RITIRATO quando glielo si chiede?

    python docs/stato-reale/banchi/m3-la-porta-mcp-serve-i-ritirati.py

Prova END-TO-END di ciò che il test in `tests/` prova solo come dichiarazione.

⚠️ PERCHÉ UNO SCRIPT E NON UN TEST: dentro pytest `verimem.mcp_server` è già
importato quando il test parte, e `HIPPO_DATA_DIR` va impostata PRIMA
dell'import o l'agente apre lo store di casa. Il primo tentativo (02/09 20:43)
falliva per questo: la risposta tornava vuota anche SENZA il flag — cioè col
controllo positivo SPENTO — e uno zero così non distingue «non c'è» da «il
banco è rotto».

Il banco è di DUE SCRITTURE, il minimo per vedere una supersessione, e pretende
il CONTROLLO POSITIVO prima di credere allo zero.
"""
from __future__ import annotations

import os
import tempfile

_D = tempfile.mkdtemp(prefix="m3mcp_")
os.environ["HIPPO_DATA_DIR"] = _D          # PRIMA dell'import: è tutto il punto
os.environ.pop("ENGRAM_DATA_DIR", None)

import asyncio  # noqa: E402
import json  # noqa: E402

from verimem import mcp_server  # noqa: E402

VECCHIO = "Il collaudo del lotto B ha rilevato 12 anomalie."
NUOVO = "Il collaudo del lotto B ha rilevato 15 anomalie."
QUERY = "quante anomalie ha rilevato il collaudo del lotto B"


async def chiama(nome: str, args: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    h = mcp_server.server.request_handlers[CallToolRequest]
    res = await h(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=nome, arguments=args)))
    p = res.root if hasattr(res, "root") else res
    t = next(c.text for c in p.content if hasattr(c, "text"))
    try:
        return json.loads(t)
    except Exception:  # noqa: BLE001
        return {"raw": t}


def main() -> int:
    ag = mcp_server._ag()
    vero = str(ag.semantic.db_path)
    print(f"  lo store del banco: {vero}")
    assert "m3mcp_" in vero, "NON è la dir temporanea: mi fermo per non toccare casa"

    a = asyncio.run(chiama("hippo_remember", {
        "proposition": VECCHIO, "topic": "banco/m3mcp",
        "source": "Verbale: collaudo lotto B, 12 anomalie rilevate."}))
    b = asyncio.run(chiama("hippo_remember", {
        "proposition": NUOVO, "topic": "banco/m3mcp",
        "source": "Verbale rev.2: collaudo lotto B, 15 anomalie rilevate."}))
    vid, nid = a.get("id"), b.get("id")
    print(f"  scritti: vecchio {vid} · nuovo {nid}")
    ag.semantic.supersede(vid, nid, principal="banco:m3",
                          reason="same-source evolution")
    print("  il vecchio è stato ritirato dal nuovo")

    senza = json.dumps(asyncio.run(
        chiama("hippo_facts_recall", {"query": QUERY, "k": 5})), ensure_ascii=False)
    con = json.dumps(asyncio.run(
        chiama("hippo_facts_recall",
               {"query": QUERY, "k": 5, "include_superseded": True})), ensure_ascii=False)

    print()
    print("  CONTROLLO POSITIVO — il SOSTITUTO torna senza il flag?", nid in senza)
    print(f"  il RITIRATO senza flag: {vid in senza}")
    print(f"  il RITIRATO con  flag : {vid in con}")
    print()
    if nid not in senza:
        print("  ⛔ CONTROLLO POSITIVO SPENTO: non torna nemmeno il sostituto,")
        print("     quindi lo zero sul ritirato NON dice niente. Banco non valido.")
        return 1
    if vid in senza:
        print("  ⛔ il ritirato torna GIÀ senza chiederlo: il banco non misura nulla.")
        return 1
    if vid not in con:
        print("  🔴 la porta MCP NON serve il ritirato nemmeno chiedendolo.")
        return 1
    print("  🟢 la porta MCP serve il ritirato SOLO quando lo si chiede.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
