"""Conta i verdetti della mappa del README — perché il contatore a mano sbagliava.

Ho postato cinque contatori sul canale (`✅ 102 · ❌ 2 · ⬜ 47` l'ultimo) senza
che nessun comando li producesse: erano **claim contati a mano mentre scrivevo**.
Alle 21:33 dell'08/09, sollecitato dal lead a portare «l'output dello script», ho
puntato il primo grep contro il mio numero e ha risposto **94 / 3 / 40**.

Le due grandezze non sono la stessa cosa — io contavo *claim*, il grep conta
*righe di tabella* — ma la differenza andava misurata, non spiegata a parole. E
la parte interessante è la direzione: sui ✅ e sui ⬜ il mio numero era **più
alto**, cioè sbagliava **a mio favore**; sui ❌ era più basso, e quel terzo ❌ si
è rivelato la **riga della legenda**, non un verdetto.

🔑 Un numero che ti dà ragione non fa attrito, quindi nessuno lo urta: l'ho
pubblicato cinque volte senza che nessuno — me compreso — lo mettesse alla prova.

Questo script è il righello, con la sua definizione dichiarata:

  riga di claim = una riga che comincia con "| " dentro una sezione "## Righe",
                  che non sia l'intestazione né il separatore della tabella.

Stampa anche **chi cade**: le righe di claim SENZA verdetto. È il controllo
positivo che può smentirmi — se la mappa avesse righe non giudicate, si accende.

Uso::

    python docs/stato-reale/banchi/ws7-conta-i-verdetti-della-mappa.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VERDE = "✅"      # ✅
ROSSO = "❌"      # ❌
BIANCO = "⬜"     # ⬜

MAPPA = Path(__file__).resolve().parents[1] / "mappa" / "README-claims.md"
_SEZIONE = re.compile(r"^## Righe (\d+)-(\d+)")


def conta(testo: str) -> dict:
    dentro = False
    claim: list[tuple[int, str]] = []
    scartate: list[tuple[int, str]] = []
    coperte_fino_a = 0
    for n, riga in enumerate(testo.splitlines(), 1):
        m = _SEZIONE.match(riga)
        if m:
            dentro = True
            coperte_fino_a = max(coperte_fino_a, int(m.group(2)))
            continue
        if riga.startswith("## ") and not m:
            dentro = False
            continue
        if not dentro or not riga.startswith("| "):
            continue
        if riga.startswith("|---"):
            continue
        # Una riga di claim comincia con il numero di riga del README. Tutto il
        # resto e' intestazione — e le intestazioni NON hanno un formato solo:
        # a meta' documento ho cambiato le etichette delle colonne ("| riga |"
        # e' diventata "| righe |"), e la prima versione di questo righello,
        # che filtrava per etichetta, se le e' ritrovate fra le righe mute.
        # Il criterio giusto e' la FORMA del dato, non il nome che gli ho dato.
        if not re.match(r"^\|\s*\*{0,2}\d", riga):
            scartate.append((n, riga))
            continue
        claim.append((n, riga))

    verdi = [n for n, r in claim if VERDE in r]
    rossi = [n for n, r in claim if ROSSO in r]
    bianchi = [n for n, r in claim if BIANCO in r]
    doppi = [n for n, r in claim if (VERDE in r and BIANCO in r)]
    muti = [(n, r) for n, r in claim if not (VERDE in r or ROSSO in r or BIANCO in r)]
    return {
        "claim": len(claim),
        "verdi": len(verdi),
        "rossi": len(rossi),
        "bianchi": len(bianchi),
        "doppi": len(doppi),
        "muti": muti,
        "righe_rosse": rossi,
        "coperte_fino_a": coperte_fino_a,
        "scartate": scartate,
    }


def main() -> int:
    testo = MAPPA.read_text(encoding="utf-8")
    r = conta(testo)
    readme = MAPPA.resolve().parents[3] / "README.md"
    totale = len(readme.read_text(encoding="utf-8", errors="replace").splitlines())

    pct = 100.0 * r["coperte_fino_a"] / totale if totale else 0.0
    print(f"mappa:   {MAPPA}")
    print(f"README:  {totale} righe")
    print("")
    print(f"coperte fino alla riga {r['coperte_fino_a']} / {totale}   ({pct:.1f}%)")
    print(f"righe di claim in tabella:  {r['claim']}")
    print(f"  con {VERDE} : {r['verdi']}")
    print(f"  con {ROSSO} : {r['rossi']}   -> righe del file: {r['righe_rosse']}")
    print(f"  con {BIANCO} : {r['bianchi']}")
    print(f"  che portano SIA {VERDE} SIA {BIANCO} (claim diviso in due): {r['doppi']}")
    print("")
    if r["muti"]:
        print(f"!! {len(r['muti'])} righe di claim SENZA verdetto:")
        for n, riga in r["muti"]:
            print(f"   riga {n}: {riga[:90]}")
        return 1
    print(f"controllo positivo: 0 righe di claim senza verdetto (su {r['claim']}).")
    print(f"righe di tabella scartate come intestazione: {len(r['scartate'])}")
    for n, riga in r["scartate"]:
        print(f"   riga {n}: {riga[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
