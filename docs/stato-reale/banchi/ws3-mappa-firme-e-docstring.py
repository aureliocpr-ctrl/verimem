"""Firme e prima riga di docstring per ogni definizione di un file — leggere
PRIMA di chiamare, su scala.

Ieri una passata a intuito ha prodotto 5 TypeError su 6 chiamate. Con 360
funzioni davanti, leggere una firma per volta a mano non è sostenibile e
indovinare non è più veloce: questo stampa, per ogni definizione, la riga, la
firma completa e la prima frase del docstring — cioè esattamente le due colonne
che la mappa chiede («funzione (file:riga)» e «cosa promette»).
"""
from __future__ import annotations

import ast
import pathlib
import sys

for percorso in sys.argv[1:]:
    p = pathlib.Path(percorso)
    albero = ast.parse(p.read_text(encoding="utf-8"))
    print(f"\n{'=' * 78}\n{p.as_posix()}\n{'=' * 78}")

    def visita(nodo: ast.AST, prefisso: str) -> None:
        for figlio in ast.iter_child_nodes(nodo):
            if isinstance(figlio, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = prefisso + figlio.name
                doc = (ast.get_docstring(figlio) or "").strip().replace("\n", " ")
                doc = doc[:150] + ("…" if len(doc) > 150 else "")
                if isinstance(figlio, ast.ClassDef):
                    print(f"\n[{figlio.lineno:5}] class {qual}")
                else:
                    args = []
                    a = figlio.args
                    for x in a.posonlyargs + a.args:
                        args.append(x.arg)
                    if a.vararg:
                        args.append("*" + a.vararg.arg)
                    elif a.kwonlyargs:
                        args.append("*")
                    for x in a.kwonlyargs:
                        args.append(x.arg + "=")
                    if a.kwarg:
                        args.append("**" + a.kwarg.arg)
                    print(f"[{figlio.lineno:5}] {qual}({', '.join(args)})")
                if doc:
                    print(f"        « {doc} »")
                else:
                    print("        « (nessun docstring) »")
                visita(figlio, qual + ".")
            else:
                visita(figlio, prefisso)

    visita(albero, "")
