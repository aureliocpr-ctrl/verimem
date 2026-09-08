"""La colonna «test che la esercita», riempita con le righe ESEGUITE.

Perche' serve, misurato l'08/09 su `verimem/mcp_server.py`: la stessa colonna
riempita col NOME (`git grep` in `tests/`, che e' quello che fa
`scripts/mappa_bozza.py`) dice il falso in due modi opposti.

  · GONFIA. Due volte su quattordici il nome che avevo controllato stava dentro
    un DOCSTRING del test: `_pavimento_di` compariva UNA volta in
    `test_avviso_mcp_stessa_soglia_dell_sdk.py`, riga 7, prosa.
  · SGONFIA. Nessun test nomina `_ok`, `_err`, `_err_proposizione_vuota` — le
    funzioni che danno forma a OGNI risposta e OGNI errore del prodotto — e
    coverage le vede accendersi tutte e tre, perche' ci si arriva DALLA PORTA.
  · E il caso peggiore: SEI file di test passano senza toccare la funzione che
    portano nel nome (`test_mcp_record_episode_with_facts` 5 passed e zero righe
    di `_build_episode`; stessa cosa per `_justified_contradicted_ids`,
    `_provider_is_configured`, `_skill_from_dict`, `_cos`, `_key_recency`).

⚠️ IL DETTAGLIO CHE DECIDE IL NUMERO: una funzione conta come esercitata solo se
una riga del suo CORPO e' stata eseguita. La riga del `def` NON basta — quella
gira alla definizione del modulo anche quando la funzione non e' mai chiamata.
Senza questa esclusione il conteggio mente al rialzo su ogni riga della mappa.

⚠️ E UN AVVERTIMENTO SUL RIGHELLO STESSO: su `_list_tools_unfiltered` (6.038
righe, corpo fatto di una sola espressione) coverage ha riportato ZERO righe di
corpo mentre due strade indipendenti provavano che era girata. Un «0» su una
funzione enorme non e' prova di codice morto: guardatelo due volte prima di
scrivere MAI CHIAMATA.

USO
    python -m coverage run --data-file=/percorso/fuori/dal/repo/.cov \\
        -m pytest <i file di test che vi attribuisce la bozza> -q
    python -m coverage json --data-file=.../.cov -o cov.json
    python scripts/mappa_coverage.py verimem/<il vostro file>.py cov.json

Nota: `pyproject.toml` mette `source = ["verimem"]`, quindi `--include` viene
IGNORATO (coverage lo dice in un warning) e traccia tutto il pacchetto: e' piu'
lento, e va bene lo stesso.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys


def intervalli(percorso: str) -> list[tuple[str, int, int]]:
    """(nome qualificato, prima riga, ultima riga) per funzioni, metodi e classi.

    I nomi sono qualificati come li vuole `scripts/mappa_completa.py`:
    `Classe.metodo`, `funzione_madre.annidata`.
    """
    albero = ast.parse(open(percorso, encoding="utf-8", errors="replace").read())
    out: list[tuple[str, int, int]] = []

    def visita(nodo: ast.AST, prefisso: str) -> None:
        for figlio in ast.iter_child_nodes(nodo):
            if isinstance(figlio, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append((prefisso + figlio.name, figlio.lineno, figlio.end_lineno))
                visita(figlio, prefisso + figlio.name + ".")
            else:
                visita(figlio, prefisso)

    visita(albero, "")
    return sorted(out, key=lambda t: t[1])


def righe_eseguite(cov_json: str, file_rel: str) -> set[int]:
    dati = json.load(open(cov_json, encoding="utf-8"))
    atteso = file_rel.replace("\\", "/")
    for k, v in dati.get("files", {}).items():
        if k.replace("\\", "/").endswith(atteso):
            return set(v["executed_lines"])
    raise SystemExit(
        f"{file_rel} non e' nel rapporto {cov_json}. "
        f"File presenti (primi 5): {list(dati.get('files', {}))[:5]}"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sorgente", help="es. verimem/mcp_server.py")
    ap.add_argument("cov_json", help="il rapporto prodotto da `coverage json`")
    ap.add_argument("--solo-spente", action="store_true",
                    help="stampa solo le funzioni con zero righe di corpo")
    a = ap.parse_args(argv)

    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    percorso = a.sorgente if os.path.isabs(a.sorgente) else os.path.join(radice, a.sorgente)
    if not os.path.exists(percorso):
        raise SystemExit(f"non trovo {percorso}")

    ese = righe_eseguite(a.cov_json, a.sorgente)
    tutte = intervalli(percorso)
    accese, spente = [], []
    for nome, primo, ultimo in tutte:
        corpo = sum(1 for ln in ese if primo < ln <= ultimo)  # esclusa la riga del def
        (accese if corpo else spente).append((nome, primo, ultimo, corpo))

    print(f"sorgente: {a.sorgente}   rapporto: {a.cov_json}")
    print(f"funzioni e classi: {len(tutte)}   "
          f"ESERCITATE: {len(accese)}   spente in questo run: {len(spente)}")
    print()
    if not a.solo_spente:
        print("== ESERCITATE (almeno una riga del CORPO eseguita) ==")
        for nome, primo, _u, n in accese:
            print(f"  `{a.sorgente}:{primo}` `{nome}` — corpo eseguito: {n} righe")
        print()
    print("== SPENTE in questo run (zero righe di corpo) ==")
    print("   NON vuol dire codice morto: vuol dire che QUESTI test non ci arrivano.")
    for nome, primo, ultimo, _n in spente:
        lung = ultimo - primo + 1
        avviso = "  ⚠️ funzione enorme: un 'zero' qui va verificato" if lung > 500 else ""
        print(f"  `{a.sorgente}:{primo}` `{nome}` — {lung} righe{avviso}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
