"""M3 — su quale asse funziona davvero il time-travel, e su quale no.

    python docs/stato-reale/banchi/m3-il-passato-torna-davvero.py

`hippo_recall_as_of` promette «point-in-time reconstruction for lawyers (state
of knowledge at signature date)» e chiude con «No competitor can answer this».
Questo banco chiede al prodotto di mantenerla, e trova che la mantiene **su un
asse solo**.

⚠️ IL LIMITE ERA GIÀ DICHIARATO, e non l'ho scoperto io: la descrizione di
`hippo_remember` lo dice per esteso, misurato il 2026-08-31 — «`asserted_at` …
is not an argument here, and passing it is ACCEPTED WITHOUT ERROR AND IGNORED
… the stored row keeps asserted_at NULL … time-travel reads (`as_of`) fall back
to the WRITE time for anything stored here — they still work, on one axis
instead of two».

Quello che mancava era la **misura**: una promessa e il suo limite vivevano in
due descrizioni che non si nominano a vicenda, e nessun banco li metteva l'una
di fronte all'altro. Un limite scritto e mai eseguito si legge come teorico.

I DUE ASSI:

    event time  (asserted_at, «quando è diventato vero»)  -> NON scrivibile qui
    write time  (created_at,  «quando l'abbiamo saputo»)  -> è questo che regge

Il banco è di DUE SCRITTURE, il minimo per vedere una supersessione — la lezione
`d2830eb27716`: «il difetto è il WRITE, non il retrieval». E qui il write è
letteralmente il punto.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time

_D = tempfile.mkdtemp(prefix="m3asof_")
os.environ["HIPPO_DATA_DIR"] = _D          # PRIMA dell'import: è tutto il punto
os.environ.pop("ENGRAM_DATA_DIR", None)

#: ⚠️ `python docs/.../questo.py` mette in `sys.path[0]` la directory DELLO
#: SCRIPT, non la radice del repo: `import verimem` prenderebbe il pacchetto
#: INSTALLATO. Chi lavora nell'albero condiviso non se ne accorge; chi lavora in
#: un `git worktree` misura l'albero di qualcun altro. Il 03/09 questo è costato
#: tre rossi a un banco gemello, tutti attribuiti al prodotto.
_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

import asyncio  # noqa: E402
import json  # noqa: E402
import sqlite3  # noqa: E402

import verimem  # noqa: E402
from verimem import mcp_server  # noqa: E402

_QUALE = pathlib.Path(verimem.__file__).resolve()
if _ROOT not in _QUALE.parents:
    raise SystemExit(
        f"⛔ sto per misurare {_QUALE}\n"
        f"   invece del repo {_ROOT}: il verdetto non direbbe niente.")

VECCHIO = "Il prezzo di listino del modello X è 1200 euro."
NUOVO = "Il prezzo di listino del modello X è 1500 euro."
QUERY = "qual è il prezzo di listino del modello X"

EVENTO_VECCHIO = time.time() - 86400 * 30   # la data VERA che proveremo a scrivere
EVENTO_NUOVO = time.time() - 86400 * 2


async def chiama(nome: str, args: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    res = await mcp_server.server.request_handlers[CallToolRequest](
        CallToolRequest(method="tools/call",
                        params=CallToolRequestParams(name=nome, arguments=args)))
    p = res.root if hasattr(res, "root") else res
    t = next(c.text for c in p.content if hasattr(c, "text"))
    try:
        return json.loads(t)
    except Exception:  # noqa: BLE001
        return {"raw": t}


def main() -> int:
    ag = mcp_server._ag()
    assert "m3asof_" in str(ag.semantic.db_path), "non è la dir temporanea"

    prima_di_scrivere = time.time()
    a = asyncio.run(chiama("hippo_remember", {
        "proposition": VECCHIO, "topic": "banco/m3asof",
        "asserted_at": EVENTO_VECCHIO,          # <- chiesto; vedremo se arriva
        "source": "Listino di allora: modello X, 1200 euro."}))
    b = asyncio.run(chiama("hippo_remember", {
        "proposition": NUOVO, "topic": "banco/m3asof",
        "asserted_at": EVENTO_NUOVO,
        "source": "Listino aggiornato: modello X, 1500 euro."}))
    vid, nid = a.get("id"), b.get("id")
    ag.semantic.supersede(vid, nid, principal="banco:m3asof",
                          reason="same-source evolution")
    dopo_aver_scritto = time.time()
    print(f"  scritti: vecchio {vid} · nuovo {nid} (ritira il primo)")

    # ── ASSE 1: event time. La porta lo accetta e lo butta? ────────────────
    con = sqlite3.connect(f"file:{ag.semantic.db_path}?mode=ro", uri=True)
    righe = {i: con.execute("SELECT asserted_at, created_at FROM facts WHERE id=?",
                            (i,)).fetchone() for i in (vid, nid)}
    con.close()
    ignorato = all(r and r[0] is None for r in righe.values())
    print()
    print("  ASSE 1 — event time (asserted_at), chiesto alla porta di scrittura")
    for i, eti in ((vid, "vecchio"), (nid, "nuovo  ")):
        print(f"     {eti}: asserted_at={righe[i][0]}  created_at={righe[i][1]:.0f}")
    print(f"     la porta ha ACCETTATO SENZA ERRORE e IGNORATO? {ignorato}")
    print("     (limite dichiarato nella descrizione di hippo_remember, 31/08)")

    # ── ASSE 2: write time. Su questo il time-travel DEVE funzionare ───────
    vuoto = json.dumps(asyncio.run(chiama(
        "hippo_recall_as_of", {"query": QUERY, "when": prima_di_scrivere - 1,
                               "k": 5})), ensure_ascii=False)
    pieno = json.dumps(asyncio.run(chiama(
        "hippo_recall_as_of", {"query": QUERY, "when": dopo_aver_scritto + 1,
                               "k": 5})), ensure_ascii=False)
    oggi = json.dumps(asyncio.run(chiama(
        "hippo_facts_recall", {"query": QUERY, "k": 5})), ensure_ascii=False)

    print()
    print("  ASSE 2 — write time (created_at)")
    print("     CONTROLLO POSITIVO — la recall di oggi torna il NUOVO?", nid in oggi)
    print("     PRIMA di scrivere, il passato è vuoto?               ",
          vid not in vuoto and nid not in vuoto)
    print("     DOPO aver scritto, il passato torna qualcosa?        ",
          vid in pieno or nid in pieno)
    print()

    if nid not in oggi:
        print("  ⛔ CONTROLLO POSITIVO SPENTO: la recall di oggi non torna nemmeno")
        print("     il sostituto, quindi nulla di ciò che precede dice niente.")
        return 1
    if vid in vuoto or nid in vuoto:
        print("  🔴 la ricostruzione di un istante PRECEDENTE alla scrittura")
        print("     restituisce fatti: non filtra affatto per tempo.")
        return 1
    if not (vid in pieno or nid in pieno):
        print("  🔴 nemmeno sull'asse del write time il passato torna: il")
        print("     time-travel non ricostruisce su NESSUN asse.")
        return 1
    if not ignorato:
        print("  🟢🟢 asserted_at ORA ARRIVA: il limite del 31/08 è stato curato,")
        print("     e questo banco va riscritto per provare i DUE assi.")
        return 0
    print("  🟡 IL TIME-TRAVEL REGGE SU UN ASSE SOLO, come dichiarato:")
    print("     ricostruisce su QUANDO L'ABBIAMO SAPUTO (write time), non su")
    print("     QUANDO ERA VERO (event time), perché la porta di scrittura MCP")
    print("     accetta asserted_at e lo scarta. Per il caso d'uso che il tool")
    print("     stesso cita — «state of knowledge at signature date» — i due")
    print("     assi coincidono solo se si scrive nell'istante in cui accade.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
