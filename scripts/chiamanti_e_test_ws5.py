"""Chi USA ogni funzione dei 15 file del lotto 1, e quale test la esercita.

Sono le due colonne che l'indice chiede (riga 11) e da cui escono i reperti.

⚠️ SI CONTANO I RIFERIMENTI, NON LE CHIAMATE. Questo righello si e' rotto due
volte oggi, e le due rotture vanno lette insieme perche' dicono la stessa cosa:

 1. `ast.Call` col nome scritto nell'import: `from .flow_events import
    emit_write as _emit_write` fa vedere `_emit_write`, e `emit_write`
    risultava a ZERO chiamanti. Preso dal controllo positivo. Ora ogni
    `import X as Y` e' registrato e l'uso di Y e' attribuito a X.
 2. `ast.Call` come unica prova d'uso: davano MAI CHIAMATA anche
      - i Protocol e le classi di tipo (`_SemanticLike`): si ANNOTANO;
      - le property (`EncodeServer.port`): si LEGGONO;
      - i callback (`_on_episode_completed`): si PASSANO a `subscribe(fn)`.
    Preso leggendo i nomi a mano, non da un controllo.

⇒ Una funzione e' usata se il suo nome COMPARE come identificatore da qualche
parte: `ast.Name` e `ast.Attribute`, non solo dentro una `ast.Call`. Il nome
nella propria `def` non conta (e' `FunctionDef.name`, non un Name node).

⚠️ Resta il limite del NOME CORTO: un nome che vive in piu' classi (`call`,
`prune`, `to_dict`) somma usi non suoi ⇒ quei conteggi sono un TETTO. E il
conteggio include il file stesso: escluderlo, il 08/09, mi ha dato 21
«candidati morti» di cui 20 falsi.

Scrive un JSON che mappa_tabella_ws5.py rilegge.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib

USCITA = os.path.join("docs", "stato-reale", "mappa", ".chiamanti-ws5.json")


def usi_per_file(radice, sottoalbero):
    """{nome_vero: [file che lo nominano]} — alias risolti, riferimenti inclusi."""
    fuori = {}
    base = pathlib.Path(radice) / sottoalbero
    if not base.exists():
        return fuori
    for f in sorted(base.rglob("*.py")):
        try:
            albero = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = f.relative_to(radice).as_posix()

        alias = {}
        for nodo in ast.walk(albero):
            if isinstance(nodo, (ast.Import, ast.ImportFrom)):
                for n in nodo.names:
                    if n.asname:
                        alias[n.asname] = n.name.split(".")[-1]

        for nodo in ast.walk(albero):
            nome = None
            if isinstance(nodo, ast.Name):
                nome = nodo.id
            elif isinstance(nodo, ast.Attribute):
                nome = nodo.attr
            if nome:
                fuori.setdefault(alias.get(nome, nome), set()).add(rel)
    return fuori


def main():
    radice = os.getcwd()
    print("leggo gli usi in verimem/ ...")
    prodotto = usi_per_file(radice, "verimem")
    print(f"  nomi distinti nominati: {len(prodotto)}")
    print("leggo gli usi in tests/ ...")
    test = usi_per_file(radice, "tests")
    print(f"  nomi distinti nominati: {len(test)}")

    dati = {
        "prodotto": {k: sorted(v) for k, v in prodotto.items()},
        "test": {k: sorted(v) for k, v in test.items()},
    }
    with open(USCITA, "w", encoding="utf-8") as fh:
        json.dump(dati, fh)

    # --- controlli positivi -----------------------------------------------
    # I primi due presero la rottura n.1; gli altri quattro sono i falsi
    # positivi della n.2, letti a mano: DEVONO risultare usati.
    casi = ("lock_import", "emit_write", "preload_embedding",
            "_SemanticLike", "port", "_on_episode_completed")
    esito = True
    for atteso in casi:
        n = len(dati["prodotto"].get(atteso, []))
        ok = n > 0
        esito = esito and ok
        print(f"CONTROLLO  {atteso:24} {n:4} file  {'ACCESO' if ok else 'ROTTO'}")
    print("=> " + ("uscita utilizzabile" if esito
                   else "NON USARE L'USCITA: un caso che doveva rispondere tace"))
    print(f"scritto {USCITA}")


if __name__ == "__main__":
    main()
