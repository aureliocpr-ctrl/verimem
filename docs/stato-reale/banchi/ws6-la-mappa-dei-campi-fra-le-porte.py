"""Quali campi ogni porta espone, sullo stesso fatto e nella stessa esecuzione.

Materiale per C3 (parita' porte). Non elenca cio' che il codice dichiara: SCRIVE
lo stesso claim con la stessa fonte su SDK e MCP, poi LEGGE, e confronta le
chiavi effettive.

ESITO misurato il 2026-08-29:
  scrittura  SDK 8 chiavi · MCP 15 · in comune 5
  lettura    SDK recall 17 · MCP facts_search 11

  🔴 `superseded_by` e' SOLO su SDK: un agente che legge via MCP non ha modo di
     sapere che il fatto che sta leggendo e' stato RITIRATO.
  🔴 lo stesso testo si chiama `text` su SDK e `proposition` su MCP, e il DB usa
     `proposition` ⇒ e' l'SDK a rinominare. Un codice portato da una porta
     all'altra prende None in silenzio, non un errore.
  ·  `warnings` (SDK) contro `anti_confab_warnings` (MCP) — conferma la cella 7.
  ·  `replaced` esiste solo su MCP.
  ·  `score` e' solo su SDK: un agente MCP non ha il punteggio di rilevanza.

⚠️ LIMITE DICHIARATO: `facts_search` potrebbe non essere la controparte esatta
di `recall`. E' pero' la porta che la guida dell'MCP indica per recuperare i
fatti, quindi e' quella che un agente userebbe. Se la controparte giusta e'
un'altra, il confronto va rifatto.

⚖️ E la differenza di CONTEGGIO non e' di per se' un difetto: una porta puo'
legittimamente esporre meno. Il difetto e' che manchi `superseded_by`, che non
e' un dettaglio di comodo ma la differenza fra un fatto vivo e uno ritirato.

    HIPPO_DATA_DIR=$(mktemp -d) python docs/stato-reale/banchi/ws6-la-mappa-dei-campi-fra-le-porte.py
"""
import asyncio
import json
import sqlite3

from verimem.config import CONFIG

assert "Temp" in str(CONFIG.semantic_db) or "tmp" in str(CONFIG.semantic_db), (
    "NON ISOLATO - questo banco scrive. Serve HIPPO_DATA_DIR su una tempdir.")

from verimem import Memory, mcp_server  # noqa: E402

CLAIM = "Il canone annuo e' 12000 EUR."


async def _mcp(nome, args):
    r = await mcp_server.call_tool(nome, args)
    testo = "".join(getattr(x, "text", str(x)) for x in r) if isinstance(r, list) else str(r)
    return json.loads(testo)


def _confronta(etichetta_a, a, etichetta_b, b):
    print(f"  {etichetta_a} ({len(a)}): {sorted(a)}")
    print(f"  {etichetta_b} ({len(b)}): {sorted(b)}")
    print(f"\n  solo {etichetta_a}: {sorted(a - b)}")
    print(f"  solo {etichetta_b}: {sorted(b - a)}")
    print(f"  in comune: {len(a & b)}")


async def main():
    m = Memory()
    sdk_w = m.add(CLAIM, topic="p/sdk", source=CLAIM)
    mcp_w = await _mcp("hippo_remember", {"proposition": CLAIM, "topic": "p/mcp", "source": CLAIM})
    print("=== CHIAVI DELLA RICEVUTA DI SCRITTURA ===")
    _confronta("SDK", set(sdk_w), "MCP", set(mcp_w))

    print("\n=== CHIAVI DI UN RISULTATO DI LETTURA ===")
    sdk_r = m.recall("Qual e' il canone?", k=1)
    mcp_r = (await _mcp("hippo_facts_search", {"query": "canone", "limit": 1})).get("items") or []
    _confronta("SDK-recall", set(sdk_r[0]) if sdk_r else set(),
               "MCP-facts_search", set(mcp_r[0]) if mcp_r else set())

    con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
    colonne = {r[1] for r in con.execute("PRAGMA table_info(facts)")}
    con.close()
    print(f"\n=== il DB usa 'proposition'? {'proposition' in colonne} "
          f"⇒ chi rinomina e' la porta che espone 'text'")


if __name__ == "__main__":
    asyncio.run(main())
