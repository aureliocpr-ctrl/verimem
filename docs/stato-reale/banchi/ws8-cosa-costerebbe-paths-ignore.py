"""Cosa cambierebbe `paths-ignore` — misurato PRIMA di decidere, non dopo.

═══ LA DOMANDA ═══
La CI e' ferma: l'ultimo `ci` verde su `main` e' del 25 agosto (W8-33). La cura
proposta e' `paths-ignore` sui percorsi che non finiscono nel wheel. Prima di
toccare `.github/` — che nessuno tocca senza claim — questo banco misura DUE
cose che la proposta deve soddisfare insieme:

  ① quanti run NON sarebbero partiti  (il guadagno)
  ② il cancello del publish troverebbe ancora un verde  (il rischio)

Il ② e' la parte che si dimentica: `publish.yml` cerca un run di `ci` sul
`github.sha`. Se l'ultimo commit e' di sola documentazione e i suoi run non
partono piu', il cancello non trova NULLA — e «nessun run» e' trattato come non
verde (verificato, W8-32). Il cancello resterebbe chiuso **per assenza**: il
modo che non si vede. Percio' `paths-ignore` va accompagnato da un cancello che
cerchi il verde sull'ultimo commit che tocca cio' che si spedisce.

═══ COME GUARDA L'ESITO DEI SOTTOPROCESSI ═══
Ogni `git` gira con `subprocess.run(..., check=False)` e il codice d'uscita
viene LETTO: se e' diverso da zero la cella stampa «⛔ EXIT=n» e il banco
prosegue dichiarando il buco, invece di leggere un output vuoto come «zero».
Un output vuoto e un comando fallito non sono la stessa cosa, e qui si vede
quale dei due e' accaduto.

═══ CONTROLLO NEGATIVO ═══
Il criterio «tocca il pacchetto» deve essere quello che decide: allargandolo a
tutto il repo, il numero DEVE cambiare. Se non cambia, il criterio non sta
misurando niente e il banco lo dice.

    rifallo con:  python docs/stato-reale/banchi/ws8-cosa-costerebbe-paths-ignore.py
"""

from __future__ import annotations

import subprocess
import sys

# Le radici che finiscono nel wheel, lette da pyproject.toml
# (`include = ["verimem*", "engram*", "hippoagent*"]`) piu' il pyproject stesso.
SPEDITO = ["verimem", "engram", "hippoagent", "pyproject.toml"]

# Il verde piu' recente di `ci` su main al momento della scrittura (W8-33).
# Non e' cablato come verita': si rigenera con il comando stampato in coda.
ULTIMO_VERDE = "18e434e3"


def git(*args: str) -> tuple[str, int]:
    """Esegue git e restituisce (output, codice d'uscita). L'esito NON si perde."""
    p = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False, timeout=300
    )
    return p.stdout.strip(), p.returncode


def conta(*args: str) -> int | None:
    """Un conteggio, oppure None se il comando e' fallito. None non e' zero."""
    out, code = git(*args)
    if code != 0 or not out:
        print(f"    ⛔ EXIT={code} su: git {' '.join(args)}  -> conteggio NON disponibile")
        return None
    try:
        return int(out)
    except ValueError:
        print(f"    ⛔ output non numerico ({out[:40]!r}): conteggio NON disponibile")
        return None


def main() -> int:
    print("=" * 74)
    print("  COSA COSTEREBBE paths-ignore — misura, non opinione")
    print("=" * 74)

    base = f"{ULTIMO_VERDE}..origin/main"

    print("\n  ① IL GUADAGNO — quanti run non sarebbero partiti")
    tutti = conta("rev-list", "--count", base)
    spediti = conta("rev-list", "--count", base, "--", *SPEDITO)
    if tutti is None or spediti is None:
        print("  ⛔ misura incompleta: NON leggere questo esito come un verdetto.")
        return 2
    print(f"    commit dall'ultimo verde a HEAD:            {tutti}")
    print(f"    di cui toccano cio' che si spedisce:        {spediti}")
    if tutti:
        print(f"    quota che accenderebbe ancora la CI:        {100 * spediti / tutti:.1f}%")
        print(f"    run risparmiati nello stesso periodo:       {tutti - spediti}")

    print("\n  ② IL RISCHIO — il cancello troverebbe ancora un verde?")
    head, c1 = git("rev-parse", "origin/main")
    ultimo_spedito, c2 = git(
        "log", "-1", "--format=%H", "origin/main", "--", *SPEDITO
    )
    if c1 != 0 or c2 != 0:
        print(f"    ⛔ EXIT={c1}/{c2}: non posso rispondere. NON e' un «va bene».")
        return 2
    print(f"    HEAD di origin/main:                        {head[:8]}")
    print(f"    ultimo commit che tocca il pacchetto:       {ultimo_spedito[:8]}")
    if head == ultimo_spedito:
        print("    ⇒ coincidono: oggi il cancello su HEAD funzionerebbe anche")
        print("      con paths-ignore. Ma e' una COINCIDENZA del momento, non")
        print("      una garanzia: al prossimo commit di sola documentazione")
        print("      HEAD si sposta e il cancello resta senza run.")
    else:
        distanza = conta("rev-list", "--count", f"{ultimo_spedito}..{head}")
        print(f"    ⇒ NON coincidono: {distanza} commit di distanza.")
        print("      Con paths-ignore, un tag su HEAD non troverebbe alcun run")
        print("      di ci e il cancello si chiuderebbe PER ASSENZA.")
        print("      ⇒ paths-ignore da solo NON basta: serve un cancello che")
        print(f"        cerchi il verde su {ultimo_spedito[:8]}, non su HEAD.")

    print("\n  ③ CONTROLLO NEGATIVO — il criterio decide davvero?")
    largo = conta("rev-list", "--count", base, "--", ".")
    if largo is None:
        print("    ⛔ controllo non eseguito: il ① resta senza conferma.")
    elif spediti == largo:
        print(f"    ⛔ allargando a tutto il repo il numero NON cambia ({largo}):")
        print("       il criterio non sta selezionando nulla. Non fidarti del ①.")
    else:
        print(f"    ✔ con tutto il repo: {largo}   ·   col solo pacchetto: {spediti}")
        print("      il criterio cambia il numero: sta decidendo qualcosa.")

    print("\n  rigenera l'ultimo verde con:")
    print("    gh api 'repos/:owner/:repo/actions/workflows/ci.yml/runs"
          "?status=success&branch=main&per_page=1' \\")
    print("       --jq '.total_count, .workflow_runs[0].head_sha'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
