"""IL CONTATORE DELLO SCRIPT, non della mia memoria (ordine del lead).

Estrae con `ast` le definizioni di un file di prodotto e dice, per ognuna, se
compare nella mappa. Il criterio è dichiarato ed è volutamente GENEROSO — il
nome fra backtick da qualche parte nel .md — perché un contatore che sovrastima
si smaschera leggendo, mentre uno che sottostima fa rifare lavoro già fatto.
Per questo stampa anche CHI manca, non solo quanti: il conteggio da solo non si
può controllare.
"""
import ast
import pathlib
import re
import sys

sorgente = pathlib.Path(sys.argv[1])
mappa = pathlib.Path(sys.argv[2])
albero = ast.parse(sorgente.read_text(encoding="utf-8"))
testo_mappa = mappa.read_text(encoding="utf-8") if mappa.exists() else ""

nomi: list[tuple[str, int]] = []
for nodo in ast.walk(albero):
    if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        if nodo.name.startswith("__") and nodo.name.endswith("__"):
            continue
        nomi.append((nodo.name, nodo.lineno))

visti, unici = set(), []
for n, riga in sorted(nomi, key=lambda x: x[1]):
    if n not in visti:
        visti.add(n)
        unici.append((n, riga))

presenti, mancanti = [], []
for n, riga in unici:
    if re.search(r"`[A-Za-z_.]*\b" + re.escape(n) + r"\b", testo_mappa):
        presenti.append((n, riga))
    else:
        mancanti.append((n, riga))

print(f"file      : {sorgente.name}")
print(f"mappa     : {mappa.name}")
print(f"definizioni (ast, dunder escluse): {len(unici)}")
print(f"nominate nella mappa             : {len(presenti)}")
print(f"MANCANTI                         : {len(mancanti)}")
print("\ncriterio: il nome compare fra backtick nel .md (generoso: sovrastima,")
print("e la sovrastima si vede leggendo le righe, il contrario no).\n")
for n, riga in mancanti:
    print(f"  MANCA  {n:38} (riga {riga})")
