#!/usr/bin/env python
"""Su quanto è vecchio il codice di cui la verifica continua sa qualcosa?

PERCHE' ESISTE
  Il 2026-08-30 abbiamo misurato la CI in molti modi — lunghezza della coda, run/ora in
  ingresso e in uscita, tempo di attraversamento, scadenze a ventiquattro ore. Nessuno di
  quei numeri risponde alla domanda di chi deve decidere se rilasciare:

      «cio' che la CI mi dice, su QUALE codice me lo dice?»

  Quel giorno la risposta era **2 giorni e 27 minuti**: il run piu' recente con tutti i
  job `test` conclusi era `#1296`, sul commit `2582a4d2` del 28/08 alle 20:44Z, mentre
  nessuno dei 402 run creati quel giorno aveva ancora finito i test.

  ⇒ «La CI e' rossa» era un'affermazione **sul 28 agosto**. E il cancello del rilascio,
  che cerca un esito verde sul commit CORRENTE, chiedeva un verdetto su qualcosa di cui la
  CI non sapeva ancora nulla: **non insoddisfatto, prematuro**.

COSA FA
  Cerca il run piu' recente in cui TUTTI i job `test` sono conclusi, e stampa l'eta' del
  suo commit. Una riga, una domanda, una risposta.

COSA NON FA
  Non dice se i test siano verdi adesso: dice **di quando** e' l'ultima cosa che sappiamo.
  E non giudica il prodotto — misura la nostra distanza dal prodotto.

    python docs/stato-reale/banchi/ws8-quanto-e-vecchio-cio-che-la-ci-sa.py
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys

#: Quante pagine da 100 scorrere per stato. Il fronte e' per definizione recente, quindi
#: una finestra corta basta — ma se il banco non trova nulla lo DICHIARA invece di
#: stampare un numero: un'assenza non e' uno zero.
PAGINE = 2
ATTESI = 6  #: job `test` per run (matrice os × versione di python)


def gh(percorso: str) -> dict:
    fatto = subprocess.run(["gh", "api", percorso], capture_output=True,
                           text=True, errors="replace", timeout=300)
    try:
        return json.loads(fatto.stdout)
    except Exception:
        return {}


def main() -> int:
    print("QUANTO E' VECCHIO CIO' CHE LA CI SA?\n")
    base = "repos/:owner/:repo/actions/workflows/ci.yml/runs"
    adesso = dt.datetime.now(dt.timezone.utc)
    migliore = None
    esaminati = 0

    for stato in ("in_progress", "completed"):
        for pagina in range(1, PAGINE + 1):
            for r in gh(f"{base}?status={stato}&per_page=100&page={pagina}").get("workflow_runs", []):
                esaminati += 1
                job = gh(f"repos/:owner/:repo/actions/runs/{r['id']}/jobs?per_page=100").get("jobs", [])
                conclusi = [x for x in job
                            if x["name"].startswith("test") and x["status"] == "completed"]
                if len(conclusi) < ATTESI:
                    continue
                if migliore is None or r["created_at"] > migliore[0]["created_at"]:
                    esiti: dict[str, int] = {}
                    for x in conclusi:
                        esiti[str(x["conclusion"])] = esiti.get(str(x["conclusion"]), 0) + 1
                    migliore = (r, esiti)
                #: ⚠️⚠️ QUI C'ERA UN `break` FUORI DALL'`if`, con accanto un commento che lo
                #: giustificava («basta il primo, sono ordinati»). Il commento descriveva
                #: un'intenzione che il codice non aveva: usciva al PRIMO run di ogni
                #: pagina, concluso o no, e il banco esaminava **3 run invece di 400**.
                #: Lo ha rivelato la riga di finestra che il banco stampa di se stesso —
                #: senza quella, un numero plausibile sarebbe passato per buono.
                #: 🔑 Un commento che GIUSTIFICA una scorciatoia e' un indizio a favore
                #: del difetto, non contro.

    if migliore is None:
        print(f"  ?  nessun run con {ATTESI} job `test` conclusi nei {esaminati} esaminati.")
        print("     Questo NON e' «zero giorni di ritardo»: e' un'astensione. O la finestra")
        print("     e' troppo corta (alza PAGINE), o la CI non ha concluso NESSUN test di")
        print("     recente — e allora il ritardo e' maggiore di quanto questo banco vede.")
        return 1

    r, esiti = migliore
    eta = adesso - dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
    print(f"  run #{r['run_number']}   sha={r['head_sha'][:8]}   creato {r['created_at'][:16]}Z")
    print(f"  esiti dei job `test`: {esiti}")
    print(f"\n  ⇒ IL VERDETTO PIU' FRESCO SUI TEST riguarda codice di {str(eta).split('.')[0]} fa.\n")
    print("  ⚖️  Non dice che i test siano rossi o verdi ADESSO: dice di QUANDO e' l'ultima")
    print("      cosa che sappiamo. Un rosso vecchio di due giorni non e' una notizia sul")
    print("      codice di oggi, ed e' cosi' che si legge male una CI in ritardo.")
    print(f"  ⚠️  Finestra: {PAGINE} pagine da 100 per stato ({esaminati} run esaminati).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
