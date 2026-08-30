"""Prima di collegare il pavimento a MCP: quanto costa, e in quale regime.

DA DOVE VIENE. Alle 22:57 ho misurato che `sotto_il_pavimento` **non e' mai
stato emesso su MCP**: il blocco cerca `_auto_relevance_floor` su `agent` e
`agent.memory`, e nessuno dei due ce l'ha (sta su `Memory`, l'SDK). Alle 23:17
@ws2 ha trovato **la via gia' in uso due volte nello stesso file**::

    from .client import Memory as _MemFloor
    _mrh = _MemFloor(path=a.semantic.db_path)._auto_relevance_floor()

⇒ Non manca il metodo: manca l'oggetto giusto. **La cura sembra due righe.**

⚠️ E SEMBRAVA DUE RIGHE ANCHE `_have_judge`, due ore fa, finche' il costo non ha
cambiato la cura (togliere il predicato avrebbe fatto pagare 21 s a ogni write
senza giudice). **Questo banco fa la stessa domanda PRIMA**, invece che dopo.

COSA HO LETTO nel codice del pavimento (`client.py:2455`), e perche' il costo
non e' uno solo:

  1. cache in-ISTANZA con TTL      -> se c'e', torna subito
  2. altrimenti legge `floor.json` -> se il corpus non e' derivato oltre
                                      `_FLOOR_DRIFT`, torna il valore salvato
  3. altrimenti RICALCOLA          -> `estimate_relevance_floor`: ~32 recall
                                      giudicati dal cross-encoder

E il docstring dichiara il numero che quel terzo ramo costa::

    explain chiamata 1:   56.845 ms      <- 57 secondi
    explain chiamata 2:      773 ms      <- la cache
    recall:                  413 ms

🔑 LA PARTE CHE RIGUARDA LA CURA PROPOSTA: `Memory(path=…)` costruisce
un'ISTANZA NUOVA a ogni chiamata ⇒ **la cache in-istanza non aiuta mai**, e
resta solo il file. Finche' il file c'e' ed e' valido si paga poco; quando
manca o e' fuori tolleranza, **si ricalcola dentro la ricerca dell'utente**.
⚠️ E che quel file possa essere in cattivo stato non e' teorico: @ws6 ne ha
trovato uno con `{"floor": 0.0}` scritto mentre l'encoding era rotto.

LA PREDIZIONE, scritta prima di eseguire: **con il file presente il costo e' di
millisecondi; senza il file e' di SECONDI**, e la differenza decide se la cura
puo' stare sul percorso di lettura o se il valore va letto in un altro modo.

CONDIZIONE DI FALSIFICAZIONE: se anche senza il file il costo restasse di
millisecondi, la cura di due righe va bene com'e' ed e' inutile complicarla.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: **la seconda chiamata, col file appena
scritto, deve costare MENO della prima.** Se costassero uguale, non starei
misurando la persistenza — starei misurando due volte la stessa strada, e i
numeri non direbbero nulla sulla cura.
═══════════════════════════════════════════════════════════════════════════════

⚠️ LIMITE DICHIARATO, e pesa: lo store di Aurelio **non si tocca** (`mode=ro` e
mai in scrittura), quindi il banco gira su uno store TEMPORANEO con pochi fatti.
La stima fa ~32 recall: su un corpus di migliaia di fatti il ricalcolo costa
PIU' di quanto si legga qui. ⇒ **Il numero di questo banco e' un PAVIMENTO del
costo, non il costo.** Se gia' qui il ricalcolo si misura in secondi, sul corpus
vero e' peggio.

    python docs/stato-reale/banchi/ws3-quanto-costa-il-pavimento-a-ogni-lettura.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FIGLIO = r'''
import json, os, sys, tempfile, time
_dir = tempfile.mkdtemp()
os.environ["HIPPO_DATA_DIR"] = _dir
from verimem.client import Memory

m = Memory()
for i in range(12):
    m.add(f"Il contratto numero {i} prevede una penale giornaliera.",
          topic=f"cost/{i}", validate="fast")

db = str(m.semantic.db_path)
f = m._floor_file()

def cronometra(con_file: bool) -> dict:
    if not con_file:
        try:
            f.unlink()
        except OSError:
            pass
    t = time.perf_counter()
    val = Memory(path=db)._auto_relevance_floor()   # istanza NUOVA, come la cura
    return {"ms": round((time.perf_counter() - t) * 1000),
            "valore": None if val is None else round(float(val), 4),
            "file_c_era": bool(con_file)}

senza = cronometra(False)      # ricalcolo: il file non c'e'
con = cronometra(True)         # ora il file e' stato scritto dal giro sopra
print(json.dumps({"senza_file": senza, "con_file": con,
                  "file": str(f), "esiste_ora": f.exists()},
                 default=str, ensure_ascii=False))
'''


def main() -> int:
    print("  LA CURA PROPOSTA: `Memory(path=a.semantic.db_path)."
          "_auto_relevance_floor()`")
    print("  — istanza NUOVA a ogni chiamata ⇒ la cache in-istanza non aiuta "
          "mai.\n")
    p = subprocess.run([sys.executable, "-c", FIGLIO],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: "
              f"{p.stderr.strip()[-260:]}")
        return 1
    d = json.loads(p.stdout.strip().splitlines()[-1])
    senza, con = d["senza_file"], d["con_file"]

    print(f"  {'regime':<26} {'ms':<8} valore")
    print("  " + "-" * 48)
    print(f"  {'SENZA floor.json':<26} {senza['ms']:<8} {senza['valore']}")
    print(f"  {'CON  floor.json':<26} {con['ms']:<8} {con['valore']}")

    print("\n  [1] CONTROLLO — la seconda deve costare MENO della prima: "
          f"{'SI' if con['ms'] < senza['ms'] else 'NO'}")
    if con["ms"] >= senza["ms"]:
        print("      CONTROLLO CADUTO: le due chiamate costano uguale ⇒ non sto")
        print("      misurando la persistenza, sto misurando due volte la stessa")
        print("      strada. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if senza["ms"] >= 1000:
        print(f"     🟡 SENZA IL FILE IL COSTO È DI SECONDI ({senza['ms']} ms).")
        print("     ⇒ La cura di due righe metterebbe QUEL costo dentro la")
        print("     ricerca dell'utente ogni volta che il file manca o è fuori")
        print("     tolleranza — e un file in cattivo stato non è teorico.")
        print("     ⇒ Prima di collegarla, si decida: leggere solo il file")
        print("     senza mai ricalcolare sul percorso di lettura, oppure")
        print("     dichiarare il costo dove il chiamante lo vede.")
    else:
        print(f"     🟢 anche senza il file il costo resta sotto il secondo "
              f"({senza['ms']} ms) su questo store: la cura di due righe va")
        print("     bene com'è, e complicarla sarebbe prematuro.")
    print(f"     Con il file: {con['ms']} ms.")

    print("\n  ⚠️ LIMITE CHE PESA: store TEMPORANEO con 12 fatti — quello di")
    print("     Aurelio non si tocca. La stima fa ~32 recall: su un corpus di")
    print("     migliaia di fatti il ricalcolo costa DI PIÙ. ⇒ questo numero è")
    print("     un PAVIMENTO del costo, non il costo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
