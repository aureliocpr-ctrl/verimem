"""La BOZZA delle righe della mappa per un file: candidati da confermare leggendo.

Per ogni funzione, metodo e classe del file (ast) stampa una riga nel formato
che scripts/mappa_completa.py riconosce, con: la prima riga del docstring
(cosa promette, secondo l'autore), i chiamanti TROVATI con git grep (da
confermare leggendo la riga: grep serve a trovare, non a contare), i file di
test che nominano il simbolo, le righe del README che lo nominano. Il
verdetto parte da NON MISURATO e la prova e' vuota: li scrive chi legge ed
esegue. Una riga senza chiamanti ne' test e' un candidato MAI CHIAMATA, da
confermare (un nome puo' essere chiamato per stringa o via getattr).

Uso:  python scripts/mappa_bozza.py verimem/x.py [> docs/stato-reale/mappa/x.md]
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys


def _radice() -> str:
    """La radice del repo: la cwd se e' un checkout (verimem/ e docs/), altrimenti
    la cartella sopra lo script. Reperto di ws1 (08/09 21:38): ancorato alla
    posizione dello script, lanciato da un altro albero descriveva quello."""
    for cand in (os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        if os.path.isdir(os.path.join(cand, "verimem")) and os.path.isdir(
            os.path.join(cand, "docs")
        ):
            return cand
    sys.exit("mappa_bozza: nessun checkout trovato (serve una cwd con verimem/ e docs/)")


RADICE = _radice()


def _git_grep(pattern: str, *paths: str) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "grep", "-n", "-E", pattern, "--", *paths],
            cwd=RADICE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout
    except OSError:
        return []
    return [r for r in out.splitlines() if r.strip()]


def _definizioni(percorso: str) -> list[tuple[str, int, str, str]]:
    albero = ast.parse(
        open(os.path.join(RADICE, percorso), encoding="utf-8", errors="replace").read()
    )
    out: list[tuple[str, int, str, str]] = []

    def visita(nodo: ast.AST, prefisso: str) -> None:
        for figlio in ast.iter_child_nodes(nodo):
            if isinstance(figlio, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = (ast.get_docstring(figlio) or "").strip().splitlines()
                prima = doc[0].strip() if doc else "(nessun docstring)"
                tipo = "classe" if isinstance(figlio, ast.ClassDef) else "funzione"
                out.append((prefisso + figlio.name, figlio.lineno, prima, tipo))
                visita(figlio, prefisso + figlio.name + ".")
            else:
                visita(figlio, prefisso)

    visita(albero, "")
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    percorso = sys.argv[1].replace("\\", "/")
    defs = _definizioni(percorso)
    readme = open(os.path.join(RADICE, "README.md"), encoding="utf-8").read().splitlines()
    print(
        f"# Mappa di `{percorso}` — {len(defs)} righe (bozza da confermare leggendo ed eseguendo)"
    )
    print()
    print(
        "| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for i, (nome, riga, prima, tipo) in enumerate(defs, 1):
        breve = nome.split(".")[-1]
        pat = r"\b" + re.escape(breve) + r"\b"
        chiamanti = [
            r
            for r in _git_grep(pat, "verimem/")
            if not r.startswith(f"{percorso}:{riga}:")
            and not re.search(r"^\S+:\d+:\s*(def|class|async def)\s+" + re.escape(breve) + r"\b", r)
        ]
        test = sorted({r.split(":", 1)[0] for r in _git_grep(pat, "tests/")})
        claim = [f"README.md:{n}" for n, riga_r in enumerate(readme, 1) if re.search(pat, riga_r)]
        chi = (
            "; ".join(f"`{r.split(':')[0]}:{r.split(':')[1]}`" for r in chiamanti[:3])
            or "nessuno trovato"
        )
        if len(chiamanti) > 3:
            chi += f" (+{len(chiamanti) - 3})"
        tt = "; ".join(f"`{t}`" for t in test[:3]) or "nessuno"
        if len(test) > 3:
            tt += f" (+{len(test) - 3})"
        cl = "; ".join(f"`{c}`" for c in claim[:3]) or "-"
        verdetto = (
            "NON MISURATO"
            if (chiamanti or test)
            else "MAI CHIAMATA (candidata: nessun chiamante ne' test trovato)"
        )
        prima = prima.replace("|", r"\|")
        print(
            f"| {i} | `{percorso}:{riga}` `{nome}` | {tipo}: {prima} | {chi} | {tt} | {cl} | {verdetto} | - |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
