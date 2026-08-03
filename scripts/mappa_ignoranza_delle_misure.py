"""La mappa dell'ignoranza, applicata alle NOSTRE misure invece che ai fatti.

PERCHE' ESISTE. Ogni difetto trovato nel dogfooding del 2-3 agosto 2026 ha la
stessa forma: una misura fatta in UNA direzione, e un prodotto usato in TUTTE.

    la misura era su          il prodotto veniva usato anche su
    ----------------------    ---------------------------------
    frasi corte               prosa da 800 caratteri
    inglese                   italiano
    `explain`                 le altre tre superfici + MCP
    il percorso fatti         il percorso documenti
    SDK -> CLI                CLI -> SDK
    il segno negativo         il positivo

Sei difetti con una forma sola. Invece di cercarne un settimo, questo script
chiede a ogni guardia del prodotto: lungo quali dimensioni sei stata misurata?

E' l'analogo di `ignorance_map`, che per ogni domanda dice se il corpus puo'
rispondere: qui per ogni soglia si dice quali variazioni dell'input sono state
considerate quando e' stata scelta.

⚠️ IL LIMITE, dichiarato perche' conta: questo legge i DOCSTRING, non il
comportamento. E' «interroga il testo, non la struttura» — l'errore che in
questo repo e' costato sei falsi allarmi in una sessione. Quindi NON e' un
verdetto su una guardia: e' un indice di DOVE CERCARE. Una guardia puo' aver
misurato una dimensione senza nominarla, e puo' non aver bisogno di tutte.

CHE COSA HA GIA' PREDETTO (2026-08-03, prima esecuzione): fra le guardie che
non citano la lunghezza c'era `trust_report._apply_ce_gate`, che passa al
cross-encoder la proposizione INTERA. Il CE tronca a 512 token, e il percorso
rerank dei fatti lo salta oltre 2000 caratteri proprio per questo — «legge solo
la testa e RIMESCOLA un ordine gia' buono», misurato il 2026-06-10. Sul corpus
vero il 5.4% dei fatti supera quella soglia. Trovato dalla mappa, non da un
altro giro di dogfooding.

Uso:  python scripts/mappa_ignoranza_delle_misure.py [--dimensione lunghezza]
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
from collections import Counter

PKG = pathlib.Path(__file__).resolve().parents[1] / "verimem"

#: Le dimensioni lungo cui l'input di un prodotto di memoria varia senza che il
#: codice se ne accorga. Ognuna e' stata la causa di almeno un difetto reale.
DIMENSIONI: dict[str, str] = {
    "lunghezza": r"\bprosa\b|\blungh|\bchar\b|caratteri|\blong\b|\bshort\b"
                 r"|frase corta|frasi corte|token window|512",
    "lingua": r"\bitalian|\benglish|\bEN\b|\bIT\b|lingua|monolingu|tedesc"
              r"|spagnol|multiling",
    "superficie": r"\bSDK\b|\bCLI\b|\bMCP\b|gateway|superfici|surface",
    "tier": r"documenti|document|episod|chunk|tier",
    "segno": r"positiv|negativ|corrobor|conflitt|conflict",
    "scala": r"corpus reale|corpus vero|\bn=\d|su \d{3,}|scala|at scale"
             r"|real corpus",
    "stato": r"quarantin|supersed|ritirat|dormant|\bvivo\b|\blive\b",
}

#: Una funzione «con una guardia»: contiene una soglia, un confronto numerico o
#: una decisione binaria su cui poggia un verdetto.
_GUARDIA = re.compile(
    r">=\s*[\d.]|<=\s*[\d.]|<\s*0\.\d|>\s*0\.\d|min_|_MIN|soglia|threshold"
    r"|floor")
#: Sotto questa lunghezza il docstring non contiene una misura da leggere.
_DOC_MINIMO = 120


def guardie() -> list[tuple[str, str, int, set[str]]]:
    fuori = []
    for f in sorted(PKG.glob("*.py")):
        try:
            albero = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for nodo in ast.walk(albero):
            if not isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            doc = ast.get_docstring(nodo) or ""
            if len(doc) < _DOC_MINIMO:
                continue
            if not _GUARDIA.search(ast.unparse(nodo)):
                continue
            coperte = {d for d, pat in DIMENSIONI.items()
                       if re.search(pat, doc, re.I)}
            fuori.append((f.name, nodo.name, len(doc), coperte))
    return fuori


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dimensione", choices=sorted(DIMENSIONI),
                    help="elenca le guardie che NON citano questa dimensione")
    ap.add_argument("--limite", type=int, default=20)
    args = ap.parse_args()

    tutte = guardie()
    print(f"guardie con una misura scritta nel docstring: {len(tutte)}\n")

    if args.dimensione:
        senza = [r for r in tutte if args.dimensione not in r[3]]
        quota = 100 * len(senza) / max(1, len(tutte))
        print(f"NON citano «{args.dimensione}»: {len(senza)} su "
              f"{len(tutte)} ({quota:.0f}%)\n")
        for f, n, ln, cop in sorted(senza, key=lambda r: -r[2])[:args.limite]:
            cita = ", ".join(sorted(cop)) or "—"
            print(f"  {f:<26} {n[:34]:<34} doc {ln:4d}  cita: {cita}")
        return 0

    c = Counter(d for _f, _n, _l, cop in tutte for d in cop)
    print(f"{'dimensione':<12} {'n':>5}   quota delle guardie")
    print("-" * 52)
    for d in DIMENSIONI:
        n = c.get(d, 0)
        barra = "#" * int(24 * n / max(1, len(tutte)))
        print(f"{d:<12} {n:5d}   {barra} {100 * n / max(1, len(tutte)):.0f}%")

    poveri = [r for r in tutte if len(r[3]) <= 1]
    quota = 100 * len(poveri) / max(1, len(tutte))
    print(f"\nguardie che citano UNA SOLA dimensione o nessuna: "
          f"{len(poveri)} su {len(tutte)} ({quota:.0f}%)")
    print("\n`--dimensione lunghezza` per la lista di dove cercare.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
