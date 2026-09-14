"""T-MAP-11, terza domanda: la cura MORDE davvero sulla porta che ho curato?

Il moat dell'ingest chiede il punteggio a `try_local_score`, che sotto
`HIPPO_ENCODE_DELEGATE_ONLY=1` NON carica il modello: lo chiede al daemon
condiviso. Se il daemon non c'e', torna None e `_grounds` fa **fail-open**:
ammette tutto. Quella variabile sta in ~/.claude/settings.json e la ereditano
tutti i processi, server MCP compreso.

Quindi la domanda non e' accademica: **la cura di stasera potrebbe essere inerte
esattamente sulla porta che ho curato.** Qui la misuro, alla porta, in due
configurazioni, con l'estrattore finto (nessuna chiamata llm vera) e il
cross-encoder VERO.

Stampa, per ogni fatto: status e `grounding_score` — dove `None` significa
«nessuno ha giudicato», che e' diverso da 0.0 («giudicato e bocciato»).

    python ws3_costo_e_fail_open.py <wt> --delegate 0|1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import time
import types

DIALOGO = ("user: Quanto costa il capannone 12?\n"
           "assistant: Il canone del capannone 12 e' 5900 euro al mese, "
           "e la consegna e' prevista per il 3 marzo.")

RIGHE = ["Il canone del capannone 12 e' 5900 euro.",
         "La consegna del capannone 12 e' prevista per il 3 marzo.",
         "Il capannone 12 e' stato venduto nel 2019.",
         "Il capannone 12 ha una superficie di 400 metri quadri.",
         "Il proprietario del capannone 12 si chiama Mario Rossi."]


class _Estrattore:
    def __init__(self):
        self.chiamate = 0

    def complete(self, system, messages, *, model=None, max_tokens=1200):
        self.chiamate += 1
        r = types.SimpleNamespace()
        r.text = "\n".join(RIGHE)
        return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("wt")
    ap.add_argument("--delegate", default="0")
    a = ap.parse_args()

    wt = pathlib.Path(a.wt).resolve()
    sys.path.insert(0, str(wt))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-costo-"))
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    os.environ["ENGRAM_DATA_DIR"] = str(tmp)
    if a.delegate == "1":
        os.environ["HIPPO_ENCODE_DELEGATE_ONLY"] = "1"
    else:
        os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)

    from verimem import mcp_server
    from verimem.semantic import SemanticMemory

    print(f"== HIPPO_ENCODE_DELEGATE_ONLY = "
          f"{os.environ.get('HIPPO_ENCODE_DELEGATE_ONLY') or '(non impostata)'}")
    sm = SemanticMemory(db_path=tmp / "porta.db")
    llm = _Estrattore()
    agente = types.SimpleNamespace(
        semantic=sm, wake=types.SimpleNamespace(llm=llm))
    mcp_server._ag = lambda: agente
    mcp_server._agent = agente

    t0 = time.time()
    fuori = asyncio.run(mcp_server._call_tool_impl("hippo_ingest_conversation", {
        "messages": [{"role": "user", "content": DIALOGO}],
        "conversation_id": "costo-1",
    }))
    dt = time.time() - t0
    esito = json.loads(fuori[0].text)
    print(f"== primo ingest (giudice FREDDO): {dt:.1f}s per {esito.get('extracted')} fatti")
    print(f"   ricevuta: stored={esito.get('stored')} quarantined={esito.get('quarantined')} "
          f"error={esito.get('error')}")
    print(f"   nota: {str(esito.get('note'))[:150]}")

    t1 = time.time()
    asyncio.run(mcp_server._call_tool_impl("hippo_ingest_conversation", {
        "messages": [{"role": "user", "content": DIALOGO}],
        "conversation_id": "costo-2",
    }))
    dt1 = time.time() - t1
    print(f"== secondo ingest (giudice CALDO): {dt1:.1f}s")

    with sqlite3.connect(str(sm.db_path)) as con:
        righe = con.execute(
            "SELECT proposition, status, grounding_score FROM facts "
            "ORDER BY rowid LIMIT 5").fetchall()
    print("== i fatti come stanno nello store (primo ingest)")
    for prop, st, gs in righe:
        marchio = "MAI GIUDICATO" if gs is None else f"{gs:.2f}"
        print(f"   {st:12s} · punteggio {marchio:>13s} · {prop[:52]}")
    quanti_senza = sum(1 for _, _, gs in righe if gs is None)
    print(f">> fatti entrati SENZA un giudizio: {quanti_senza}/{len(righe)}")


if __name__ == "__main__":
    main()
