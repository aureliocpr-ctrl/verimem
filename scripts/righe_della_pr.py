#!/usr/bin/env python3
"""Il tetto delle righe di una PR (regola R6: piccolo e rivisto).

Conta le righe di PRODOTTO **aggiunte** da una PR e fallisce oltre 300. Le
cancellazioni non contano: togliere codice è la cosa che vogliamo incoraggiare,
e contarla come «grande» punirebbe proprio quella.

    python scripts/righe_della_pr.py <base> <head>          # verdetto, uscita 0/1
    python scripts/righe_della_pr.py <base> <head> --deroga # solo avviso, uscita 0
    python scripts/righe_della_pr.py --autotest             # prova che morde

COSA CONTA COME PRODOTTO — il criterio, che vale quanto il numero: i file sotto
`verimem/` (il pacchetto pubblicato). NON contano test, documenti, script,
workflow e banchi: una PR che aggiunge 400 righe di test a 50 di prodotto è una
PR piccola ben provata, e un tetto che la bocciasse insegnerebbe a scrivere meno
test. Il conteggio dei file esclusi si stampa lo stesso, così chi legge vede la
PR intera e non solo la parte sorvegliata.

PERCHÉ 300 E NON 100 — la fonte primaria (Google, *Small CLs*) dà «100 lines»
come misura ragionevole e «1000 lines is usually too large». 300 è il numero
scelto dall'agenzia il 09/09 e sta in mezzo: non è un numero di Google, è il
nostro, e come tutti i nostri va rimisurato se morde troppo o mai. La deroga
esiste ed è nominale: l'etichetta `lotto-grande` sulla PR, che solo il lead
mette. Una deroga che chiunque può darsi da solo non è una deroga.

Misurato il 09/09/2026.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

TETTO = 300
PREFISSI_PRODOTTO = ("verimem/",)
ETICHETTA_DI_DEROGA = "lotto-grande"


def numstat(base: str, head: str, cwd: str | None = None) -> list[tuple[int, int, str]]:
    """`git diff --numstat base...head` -> [(aggiunte, tolte, percorso)].

    `...` (tre punti) e non `..`: si contano le righe che la PR **aggiunge al
    suo ramo**, non quelle che main ha nel frattempo aggiunto altrove. Con due
    punti una PR ferma diventa «grande» perché main è andato avanti.
    """
    uscita = subprocess.run(
        ["git", "diff", "--numstat", f"{base}...{head}"],
        capture_output=True, text=True, check=True, cwd=cwd,
    ).stdout
    righe = []
    for riga in uscita.splitlines():
        pezzi = riga.split("\t")
        if len(pezzi) != 3:
            continue
        aggiunte, tolte, percorso = pezzi
        if aggiunte == "-" or tolte == "-":   # binario: git non sa contarlo
            righe.append((0, 0, percorso))
            continue
        righe.append((int(aggiunte), int(tolte), percorso))
    return righe


def misura(righe: list[tuple[int, int, str]]) -> dict:
    prodotto = [r for r in righe if r[2].startswith(PREFISSI_PRODOTTO)]
    altro = [r for r in righe if not r[2].startswith(PREFISSI_PRODOTTO)]
    return {
        "aggiunte_prodotto": sum(a for a, _, _ in prodotto),
        "tolte_prodotto": sum(t for _, t, _ in prodotto),
        "aggiunte_altro": sum(a for a, _, _ in altro),
        "tolte_altro": sum(t for _, t, _ in altro),
        "file_prodotto": sorted(p for _, _, p in prodotto),
        "file_altro": sorted(p for _, _, p in altro),
    }


def stampa(m: dict, deroga: bool) -> int:
    print(f"righe_della_pr.py — tetto {TETTO} righe di prodotto AGGIUNTE "
          f"(prodotto = {', '.join(PREFISSI_PRODOTTO)})")
    print()
    print(f"  prodotto : +{m['aggiunte_prodotto']:5d}  -{m['tolte_prodotto']:5d}   "
          f"{len(m['file_prodotto'])} file")
    for percorso in m["file_prodotto"][:30]:
        print(f"       {percorso}")
    if len(m["file_prodotto"]) > 30:
        print(f"       ... e altri {len(m['file_prodotto']) - 30}")
    print(f"  il resto : +{m['aggiunte_altro']:5d}  -{m['tolte_altro']:5d}   "
          f"{len(m['file_altro'])} file (test, documenti, script, workflow: fuori dal tetto)")
    print()
    if m["aggiunte_prodotto"] <= TETTO:
        print(f"VERDETTO: VERDE — {m['aggiunte_prodotto']} <= {TETTO}.")
        return 0
    if deroga:
        print(f"VERDETTO: VERDE PER DEROGA — {m['aggiunte_prodotto']} > {TETTO}, ma la PR porta "
              f"l'etichetta `{ETICHETTA_DI_DEROGA}`.")
        return 0
    print(f"VERDETTO: ROSSO — {m['aggiunte_prodotto']} > {TETTO} righe di prodotto aggiunte.")
    print("  Cura: spezza la PR in una cosa sola per volta (un ticket, un ramo, una PR).")
    print(f"  Se il lotto grande è voluto, il LEAD mette l'etichetta `{ETICHETTA_DI_DEROGA}` "
          "sulla PR: la deroga è nominale, non automatica.")
    return 1


def autotest() -> int:
    """Il controllo positivo: 301 righe di prodotto DEVONO uscire 1, e 301 di test no."""
    esiti = []
    casi = [
        ("PR piccola (299 di prodotto)", [(299, 0, "verimem/x.py")], False, 0),
        ("PR al tetto esatto (300)", [(300, 0, "verimem/x.py")], False, 0),
        ("PR grande (301 di prodotto)", [(301, 0, "verimem/x.py")], False, 1),
        ("PR grande CON deroga", [(301, 0, "verimem/x.py")], True, 0),
        ("400 righe di TEST e 50 di prodotto",
         [(400, 0, "tests/test_x.py"), (50, 0, "verimem/x.py")], False, 0),
        ("una cancellazione enorme", [(0, 5000, "verimem/x.py")], False, 0),
    ]
    for nome, righe, deroga, atteso in casi:
        print(f"=== {nome} ===")
        avuto = stampa(misura(righe), deroga)
        ok = avuto == atteso
        esiti.append(ok)
        print(f"    atteso {atteso}, avuto {avuto}  {'OK' if ok else 'ROSSO'}\n")
    if all(esiti):
        print(f"AUTOTEST VERDE: {len(esiti)} casi su {len(esiti)} — il tetto morde e non morde a caso.")
        return 0
    print(f"AUTOTEST ROSSO: {esiti.count(False)} casi su {len(esiti)} sbagliati.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base", nargs="?", help="lo sha di partenza (base della PR)")
    parser.add_argument("head", nargs="?", help="lo sha di arrivo (punta della PR)")
    parser.add_argument("--deroga", action="store_true",
                        help=f"la PR porta l'etichetta `{ETICHETTA_DI_DEROGA}` (la mette il lead)")
    parser.add_argument("--autotest", action="store_true")
    argomenti = parser.parse_args(argv)
    if argomenti.autotest:
        return autotest()
    if not argomenti.base or not argomenti.head:
        parser.error("servono base e head (oppure --autotest)")
    return stampa(misura(numstat(argomenti.base, argomenti.head)), argomenti.deroga)


if __name__ == "__main__":
    sys.exit(main())
