"""Lo STESSO testo, due porte di scrittura, due esiti opposti — ed e' voluto.

DA DOVE VIENE. Cercavo un difetto e non l'ho trovato: sospettavo che la nota di
`hippo_transcript_promote` — *«promoted as low-trust model_claim»* — affermasse
uno status invece di leggerlo, come faceva quella dell'ingest fino a stasera.
**Misurato, la nota dice il vero**: due turni, uno neutro e uno auto-affermativo,
escono **entrambi** `model_claim`. Il sospetto cade.

🔑 MA LA MISURA HA MOSTRATO ALTRO, ed e' piu' utile del difetto che cercavo::

    testo identico: «Ho verificato che il fix funziona.»

    hippo_remember             ->  quarantined   L1.10, L1.15, L1.20
    hippo_transcript_promote   ->  model_claim   (nessuno strato)

⇒ **Lo stesso testo entra nel corpus da una porta e ne resta fuori dall'altra.**
Un `model_claim` e' **recuperabile**; un quarantinato e' memorizzato ma **tenuto
FUORI dal recall di default**.

⚖️ NON E' UN DIFETTO, ed e' la ragione per cui questo banco non propone una
cura: promuovere un turno di conversazione e' **registrare che una cosa e' stata
detta**, non affermarla — la stessa distinzione che il prodotto fa con
`meta_narrative` (*«un checkpoint che dice "done" e' un record di lavoro, non
un'affermazione sul mondo»*). E la nota della porta lo dichiara: *«raw chat is
NOT auto-verified — supply evidence to elevate status»*.

⚠️ MA VA DETTO, e questo e' il punto: **chi promuove un turno mette nel recall
un testo che la porta principale avrebbe trattenuto.** La differenza non e' nel
contenuto: e' in **cosa si dichiara di stare facendo**. Chi legge il corpus piu'
tardi vede un `model_claim` e non sa da quale delle due porte sia arrivato —
a meno di guardare la provenance.

LA PREDIZIONE, scritta prima di eseguire: la nota di `transcript_promote` mente
come quella dell'ingest.
**CADUTA**: la nota dice il vero su entrambi i turni provati.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: `hippo_remember` sullo STESSO testo deve
quarantinare. Se ammettesse anche lui, non ci sarebbe nessuna differenza da
misurare e il banco parlerebbe di un fenomeno che non esiste.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO, entrambe le porte in-process, italiano.
Lo store di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-lo-stesso-testo-da-due-porte-di-scrittura.py
"""

from __future__ import annotations

import json
import subprocess
import sys

AUTOCLAIM = "Ho verificato che il fix funziona."
NEUTRO = "La penale del contratto e' 120 euro al giorno."

FIGLIO = r'''
import asyncio, json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
from verimem import mcp_server
from verimem.transcript_index import TranscriptIndex, Turn

autoclaim, neutro = sys.argv[1], sys.argv[2]
idx = TranscriptIndex()
righe = []

for etichetta, testo in (("auto-affermativo", autoclaim), ("neutro", neutro)):
    tid = idx.store(Turn(text=testo, session_id="s1"))
    d = json.loads(asyncio.run(mcp_server._call_tool_impl(
        "hippo_transcript_promote", {"turn_id": tid, "topic": "due/p"}))[0].text)
    righe.append({"porta": "transcript_promote", "caso": etichetta,
                  "status": d.get("status"), "lay": [], "nota": str(d.get("note"))[:60]})

for etichetta, testo in (("auto-affermativo", autoclaim), ("neutro", neutro)):
    d = json.loads(asyncio.run(mcp_server._call_tool_impl(
        "hippo_remember",
        {"proposition": testo, "topic": "due/r", "validate": "full"}))[0].text)
    lay = [str(w.get("layer")) for w in (d.get("anti_confab_warnings") or [])
           if isinstance(w, dict)]
    righe.append({"porta": "remember", "caso": etichetta,
                  "status": d.get("status"), "lay": lay, "nota": ""})

print(json.dumps(righe, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO, AUTOCLAIM, NEUTRO],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-240:]}")
        return 1
    righe = json.loads(p.stdout.strip().splitlines()[-1])

    print(f"  {'porta':<20} {'caso':<18} {'status':<13} strati")
    print("  " + "-" * 74)
    for r in righe:
        print(f"  {r['porta']:<20} {r['caso']:<18} {str(r['status']):<13} "
              f"{','.join(r['lay']) or '-'}")

    def _stato(porta: str, caso: str) -> str:
        for r in righe:
            if r["porta"] == porta and r["caso"] == caso:
                return str(r["status"])
        return "?"

    rem = _stato("remember", "auto-affermativo")
    pro = _stato("transcript_promote", "auto-affermativo")

    print("\n  [1] CONTROLLO — `remember` sullo stesso testo DEVE quarantinare: "
          f"{'SI' if rem == 'quarantined' else 'NO'}")
    if rem != "quarantined":
        print("      CONTROLLO CADUTO: nessuna differenza da misurare, il")
        print("      fenomeno non si presenta. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if pro != rem:
        print(f"     🟡 LO STESSO TESTO: `remember` -> {rem} · "
              f"`transcript_promote` -> {pro}.")
        print("     ⇒ Da una porta resta FUORI dal recall di default, dall'altra")
        print("     ci entra. NON e' un difetto: promuovere un turno e'")
        print("     registrare che una cosa e' stata DETTA, non affermarla, e la")
        print("     nota della porta lo dichiara. ⚠️ Ma chi legge il corpus piu'")
        print("     tardi vede un `model_claim` e non sa da quale porta venga,")
        print("     se non guardando la provenance.")
    else:
        print(f"     🟢 le due porte danno lo STESSO esito ({pro}): non c'e'")
        print("     asimmetria da dichiarare.")

    print("\n  ⚠️ LIMITI: due testi, italiano, un processo. Non misura QUANTO")
    print("     spesso si promuovano turni, ne' quanti fatti del corpus vengano")
    print("     da li' — quel conto e' un'altra misura.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
