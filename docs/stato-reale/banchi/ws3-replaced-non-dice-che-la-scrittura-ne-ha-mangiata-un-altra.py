"""La ricevuta dice `replaced`, e non e' la domanda che il chiamante ha.

DA DOVE VIENE. Alle 21:33 del 30/08 @ws2 ha misurato che **43 fatti su 832
scritti in 24 ore sono stati mangiati da una scrittura successiva**, 32 dei
quali entro 60 secondi: le due braccia di un A/B, due punti della stessa curva,
due campi dello stesso soggetto. La sua cura e' di PROCESSO — *un topic per
misura* — e regge. **La domanda di PRODOTTO accanto e' un'altra**, ed e' nel
perimetro di chi guarda cosa la porta DICE:

    quando una scrittura ne mangia un'altra, la ricevuta lo dice a chi scrive?

C'E' UN CAMPO CHE SEMBRA RISPONDERE, e si chiama `replaced`. ⚠️ Ma il commento
del prodotto, a `mcp_server.py` sopra il punto in cui viene calcolato, dice
un'altra cosa::

    «every hippo_remember call generates a fresh random id, the SELECT
     pre-INSERT check never matches, was_replaced is always False, outcome is
     always "ok_new" … Replacement is only triggered when a CALLER passes an
     explicit fact.id that already exists»

⇒ `replaced` e' il rimpiazzo **per id identico**, non la **supersessione**. Sono
due meccanismi diversi con due nomi vicini, e il secondo e' quello che mangia i
fatti.

LA PREDIZIONE, scritta prima di eseguire: **la seconda scrittura mangia la prima
e la sua ricevuta riporta `replaced=False`** — cioe' il campo dice il vero sulla
propria domanda e **non risponde a quella che il chiamante ha davvero**.

CONDIZIONE DI FALSIFICAZIONE: se `replaced` diventasse `True` sulla scrittura
che supersede, il campo risponderebbe eccome e non ci sarebbe niente da dire.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: **la supersessione deve AVVENIRE**. Se i
due fatti restassero entrambi vivi, un `replaced=False` non direbbe nulla —
misurerei una ricevuta onesta su un evento che non e' successo. Il banco legge
`superseded_by` dal DB del prodotto e si ferma se e' vuoto.
⚠️ E i due fatti devono essere AMMESSI: un quarantinato non entra nel percorso
della supersessione (misurato il 30/08 alle 20:30, su un banco che si e'
rifiutato di concludere proprio per questo).
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO, porta MCP in-process, due claim sullo
stesso soggetto e sullo stesso topic, **due fonti che SOSTENGONO** ciascuna il
proprio claim, scritte a meno di un secondo l'una dall'altra — il caso che @ws2
ha misurato sul corpus vero. Lo store di Aurelio non e' toccato. Il primo write
paga il caricamento del giudice (~33 s).

    python docs/stato-reale/banchi/ws3-replaced-non-dice-che-la-scrittura-ne-ha-mangiata-un-altra.py
"""

from __future__ import annotations

import json
import subprocess
import sys

A = "Il paziente Rossi e' DECEDUTO."
FONTE_A = "Referto del 12 marzo: il paziente Rossi risulta deceduto."
B = "Il paziente Rossi e' stato DIMESSO."
FONTE_B = "Referto del 12 marzo: il paziente Rossi e' stato dimesso."

FIGLIO = r'''
import asyncio, json, os, sqlite3, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
a_txt, fa, b_txt, fb = sys.argv[1:5]
from verimem import mcp_server

def scrivi(prop, fonte, i):
    out = asyncio.run(mcp_server._call_tool_impl(
        "hippo_remember",
        {"proposition": prop, "topic": "sup/x", "source": fonte,
         "validate": "full"}))
    d = json.loads(out[0].text)
    return {"i": i, "id": d.get("id"), "status": d.get("status"),
            "replaced": d.get("replaced"), "moat": str(d.get("moat"))[:44],
            "chiavi_supersessione": sorted(
                k for k in d if "supers" in k.lower() or "retir" in k.lower()
                or "sostitu" in k.lower())}

ricevute = [scrivi(a_txt, fa, 1), scrivi(b_txt, fb, 2)]

from verimem.config import CONFIG
righe = []
with sqlite3.connect(str(CONFIG.semantic_db)) as c:
    c.row_factory = sqlite3.Row
    for r in c.execute("SELECT id, proposition, status, superseded_by FROM facts"):
        righe.append({"id": r["id"], "p": r["proposition"][:30],
                      "status": r["status"], "sup": r["superseded_by"]})
print(json.dumps({"ricevute": ricevute, "db": righe}, ensure_ascii=False))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO, A, FONTE_A, B, FONTE_B],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-250:]}")
        return 1
    d = json.loads(p.stdout.strip().splitlines()[-1])

    print("  LE DUE RICEVUTE, dalla porta MCP")
    intestazione = "campi che nominano la supersessione"
    print(f"  {'#':<3} {'status':<13} {'replaced':<10} {intestazione:<34}")
    print("  " + "-" * 74)
    for r in d["ricevute"]:
        print(f"  {r['i']:<3} {str(r['status']):<13} {str(r['replaced']):<10} "
              f"{str(r['chiavi_supersessione'] or 'NESSUNO'):<34}")

    print("\n  LO STORE, subito dopo")
    for r in d["db"]:
        print(f"     {r['id'][:12]}  {r['p']:<32} {r['status']:<13} "
              f"superseded_by={r['sup']}")

    mangiato = [r for r in d["db"] if r["sup"]]
    print("\n  [1] CONTROLLO — la supersessione E' AVVENUTA: "
          f"{'SI' if mangiato else 'NO'}")
    if not mangiato:
        print("      CONTROLLO CADUTO: i due fatti sono entrambi vivi ⇒ un")
        print("      `replaced=False` non direbbe niente, perche' non c'e'")
        print("      stato niente da dire. NESSUN VERDETTO.")
        return 1
    if any(r["status"] == "quarantined" for r in d["db"]):
        print("      ⚠️ un fatto e' quarantinato: la popolazione non e' quella")
        print("      voluta (un quarantinato non entra nella supersessione).")

    seconda = d["ricevute"][-1]
    print("\n  ══ VERDETTO ══")
    if seconda["replaced"] in (False, None) and not seconda["chiavi_supersessione"]:
        print("     🔴 LA RICEVUTA NON LO DICE. La seconda scrittura ha mangiato")
        print(f"     la prima e la sua ricevuta riporta replaced="
              f"{seconda['replaced']}, senza nessun campo che nomini la")
        print("     supersessione.")
        print("     ⇒ `replaced` risponde alla SUA domanda (rimpiazzo per id")
        print("     identico) e NON a quella che il chiamante ha davvero. Chi")
        print("     scrive due misure vicine non ha modo di accorgersene DALLA")
        print("     PORTA: deve andare a guardare `superseded_by` nello store.")
    elif seconda["replaced"]:
        print("     🟢 LA RICEVUTA LO DICE: `replaced` diventa vero sulla")
        print("     scrittura che supersede ⇒ la mia lettura del commento era")
        print("     incompleta e lo dico.")
    else:
        print("     🟡 `replaced` non lo dice, ma un ALTRO campo lo nomina: "
              f"{seconda['chiavi_supersessione']}")

    print("\n  ⚠️ LIMITI: un caso, due scritture, italiano, una sola porta")
    print("     (MCP). Non misura QUANTO spesso accada — quel numero e' di")
    print("     @ws2 (43 su 832 in 24 h, 32 entro 60 secondi) — ne' se l'SDK")
    print("     si comporti allo stesso modo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
