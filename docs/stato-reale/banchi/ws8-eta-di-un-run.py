"""L'eta' di un run della CI, senza il conto a mente che sbaglio ogni volta.

═══ PERCHE' ESISTE ═══
Tre volte in due giorni ho confrontato un `created_at` dell'API — che e' in
**UTC** — con l'orologio locale, e ne ho ricavato eta' sbagliate che ho poi
pubblicato sul canale. L'ultima, il 01/09: «sei job in corso da 2h11m, fuori dal
profilo noto». Il run aveva **undici minuti** ed era perfettamente nel profilo;
l'allarme era interamente mio.

La regola «le date dell'API sono UTC» era gia' scritta nella mia lista degli
errori, e l'ho riletta prima di sbagliare. ⇒ **Una regola riletta e non
applicata vale zero: il presidio e' uno strumento che fa il conto al posto
mio.**

═══ COSA STAMPA, E PERCHE' COSI' ═══
Per ogni run: lo stato, l'istante di creazione **in entrambi i fusi**, e l'eta'
in minuti calcolata su timestamp consapevoli del fuso (`datetime` con
`timezone.utc`), mai su stringhe. Stampa **anche l'ora locale e quella UTC del
momento in cui gira**: chi legge il verdetto tre ore dopo deve poter vedere da
che istante e' misurato — un'eta' senza il suo istante inganna quanto un
rapporto senza finestra.

═══ COME GUARDA L'ESITO DEL SOTTOPROCESSO ═══
`gh` gira con `check=False` e il codice d'uscita viene LETTO: se e' diverso da
zero la cella stampa «⛔ EXIT=n» e il banco si ferma dichiarando il buco, invece
di leggere un elenco vuoto come «nessun run». Un output vuoto e un comando
fallito non sono la stessa cosa.

    rifallo con:  python docs/stato-reale/banchi/ws8-eta-di-un-run.py [branch]
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys

API = "repos/:owner/:repo/actions/workflows/ci.yml/runs"


def _gh(url: str) -> tuple[dict, int]:
    p = subprocess.run(
        ["gh", "api", url], capture_output=True, text=True, check=False, timeout=180
    )
    if p.returncode != 0:
        return {}, p.returncode
    try:
        return json.loads(p.stdout), 0
    except ValueError:
        return {}, 99


def _eta_minuti(creato_iso: str, adesso: dt.datetime) -> float:
    """Entrambi consapevoli del fuso: nessun confronto fra UTC e orologio locale."""
    creato = dt.datetime.fromisoformat(creato_iso.replace("Z", "+00:00"))
    return (adesso - creato).total_seconds() / 60


def main() -> int:
    branch = sys.argv[1] if len(sys.argv) > 1 else "main"
    adesso = dt.datetime.now(dt.timezone.utc)
    locale = adesso.astimezone()

    print(f"  misurato alle {locale:%H:%M} locali  ({adesso:%H:%M} UTC)  ·  branch={branch}")

    dati, code = _gh(f"{API}?branch={branch}&per_page=8")
    if code != 0:
        print(f"  ⛔ EXIT={code} da gh: NON leggere questo come «nessun run».")
        return 2
    run = dati.get("workflow_runs", [])
    if not run:
        print("  (nessun run su questo branch — e il comando e' riuscito: EXIT=0)")
        return 0

    print(f"  {'run':>7}  {'stato':<22} {'creato UTC':<17} {'creato locale':<15} tempo")
    for r in run:
        creato = dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        # Per un run CONCLUSO il numero utile e' la DURATA (created -> updated);
        # per uno ancora vivo e' l'ETA' (created -> adesso). Stamparli con la
        # stessa etichetta e' come confondere «quanto ci ha messo» con «da
        # quanto aspetta»: il difetto e' stato trovato usando questo banco, che
        # dava 44,1 ore a un run durato 34 perche' misurava fino a oggi.
        concluso = r["status"] == "completed"
        fine = (
            dt.datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))
            if concluso
            else adesso
        )
        minuti = (fine - creato).total_seconds() / 60
        stato = f"{r['status']}/{r['conclusion'] or '-'}"
        quanto = f"{minuti:.0f} min" if minuti < 90 else f"{minuti / 60:.1f} ore"
        etichetta = "durata" if concluso else "in attesa da"
        print(
            f"  #{r['run_number']:>6}  {stato:<22} {creato:%m-%d %H:%M} UTC   "
            f"{creato.astimezone():%m-%d %H:%M}      {etichetta} {quanto}"
        )

    print("\n  ⚠️ Il tetto noto di un run e' ~45 min (windows 45,0 · ubuntu 17,5 ·")
    print("     macos 22,1, dal commento in ci.yml). Un'eta' sopra quella soglia e'")
    print("     ATTESA IN CODA, non lentezza dei test: sono due diagnosi diverse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
