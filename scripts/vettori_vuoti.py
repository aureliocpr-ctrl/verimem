#!/usr/bin/env python3
"""Quanti fatti sono nello store SENZA vettore (il controllo del postmortem del 09/09).

    python scripts/vettori_vuoti.py                 # sullo store di questo utente
    python scripts/vettori_vuoti.py --db <file.db>  # su uno store preciso
    python scripts/vettori_vuoti.py --autotest      # prova che il controllo morde

Un fatto salvato mentre il daemon di encoding è freddo entra con un vettore
**differito** — un blob di zero byte — ed è trovabile solo per parola chiave,
non dal recall semantico. È un comportamento voluto (`verimem facts backfill
--help`: «persists the row instantly … so it never cold-blocks ~22s»), e la
cura è `verimem facts backfill`, idempotente. Il problema è che **nessuno se ne
accorge**: la ricevuta del `save` stampa `stored=True` e non lo dice.

⚠️ PERCHÉ NON BASTA `WHERE embedding IS NULL` — misurato il 09/09/2026 sullo
store di casa, dopo che quattordici fatti erano entrati senza vettore in 18
minuti:

    WHERE embedding IS NULL     ->  0     <- il controllo ovvio non ne vede nessuno
    WHERE length(embedding)=0   -> 14     <- ci sono tutti

Un blob di zero byte **non è NULL**, e `embedding_model = ''` **non è NULL**.
Chi aveva appena dichiarato «lo store è pulito» aveva usato il primo criterio, e
la dichiarazione era vera e inutile insieme. Qui si conta per **forma**:
`NULL` · `VUOTO` · la lunghezza in byte — e la composizione si stampa SEMPRE,
anche quando è verde, perché un numero senza la sua composizione non si difende.

⚠️ E IL DATABASE È QUELLO ANNIDATO: `<data_dir>/semantic.db` esiste ed è VUOTO
(0 fatti); quello vero è `<data_dir>/semantic/semantic.db`. Un controllo puntato
sul primo dice «zero fatti senza vettore» ed è cieco, non pulito. Questo script
prende il DB da `CONFIG` e **stampa il percorso che ha letto**.

Solo lettura: apre con `mode=ro`.
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import sqlite3
import sys

TETTO_VUOTI = 0

FORMA = (
    "CASE WHEN embedding IS NULL THEN 'NULL' "
    "WHEN length(embedding)=0 THEN 'VUOTO' "
    "ELSE CAST(length(embedding) AS TEXT) END"
)


def db_dello_store() -> pathlib.Path:
    """Il DB vero: quello ANNIDATO, non l'omonimo alla radice di data_dir."""
    from verimem.config import CONFIG

    base = pathlib.Path(CONFIG.data_dir)
    annidato = base / "semantic" / "semantic.db"
    return annidato if annidato.exists() else base / "semantic.db"


def _quando(valore) -> str:
    try:
        return datetime.datetime.fromtimestamp(float(valore)).strftime("%d/%m %H:%M:%S")
    except (TypeError, ValueError):
        return str(valore)[:19]


def _colonna_del_testo(con: sqlite3.Connection) -> str:
    """La colonna col testo del fatto si chiama `proposition`, non `text`.

    Scritto qui perche' il primo autotest di questo script passava tutto e lo
    script cadeva sullo store vero con `no such column: text`: il banco finto
    aveva uno schema inventato da me. Un banco che non riproduce lo schema vero
    prova solo che il banco e' coerente con se stesso (09/09/2026).
    """
    nomi = [r[1] for r in con.execute("PRAGMA table_info(facts)")]
    for candidato in ("proposition", "text", "content"):
        if candidato in nomi:
            return candidato
    raise RuntimeError(f"nessuna colonna di testo in facts: {nomi}")


def misura(db: pathlib.Path) -> dict:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        testo = _colonna_del_testo(con)
        righe = list(con.execute(
            f"SELECT {FORMA} AS forma, COALESCE(embedding_model,'<NULL>'), COUNT(*), "
            f"MIN(created_at), MAX(created_at) FROM facts GROUP BY forma, 2 ORDER BY 3 DESC"
        ))
        vuoti = [r for r in con.execute(
            f"SELECT id, substr({testo},1,58), created_at FROM facts "
            f"WHERE embedding IS NULL OR length(embedding)=0 ORDER BY created_at"
        )]
    finally:
        con.close()
    return {"db": str(db), "composizione": righe, "vuoti": vuoti}


def stampa(risultato: dict, quanti_nomi: int = 20) -> int:
    print(f"vettori_vuoti.py — {risultato['db']}")
    print()
    print("  composizione per FORMA del vettore (non `IS NULL`: non vedrebbe i vuoti)")
    totale = 0
    for forma, modello, quanti, primo, ultimo in risultato["composizione"]:
        totale += quanti
        print(f"    {quanti:>6}  emb={forma:>6}  modello='{modello[:34]}'  "
              f"{_quando(primo)} -> {_quando(ultimo)}")
    print(f"    {totale:>6}  in tutto")
    print()
    vuoti = risultato["vuoti"]
    if not vuoti:
        print(f"VERDETTO: VERDE — nessun fatto senza vettore (tetto {TETTO_VUOTI}).")
        return 0
    print(f"  i {len(vuoti)} fatti senza vettore, per nome:")
    for id_fatto, testo, quando in vuoti[:quanti_nomi]:
        print(f"    {id_fatto}  {_quando(quando)}  {testo}…")
    if len(vuoti) > quanti_nomi:
        print(f"    … e altri {len(vuoti) - quanti_nomi}")
    print()
    print(f"VERDETTO: ROSSO — {len(vuoti)} fatti sono fuori dal recall semantico "
          f"(tetto {TETTO_VUOTI}).")
    print("  Cura: `python -m verimem.cli facts backfill` (idempotente) — ma PRIMA")
    print("  controlla che il daemon di encoding sia vivo e dichiari il modello della")
    print("  config: se serve un'altra dimensione, il backfill scrive vettori che il")
    print("  recall non sa leggere, e il danno peggiora invece di chiudersi.")
    return 1


def autotest() -> int:
    """Il controllo positivo: un vettore vuoto DEVE far uscire 1, e uno pieno 0."""
    import tempfile

    esiti = []
    for nome, blob, atteso in (("un vettore pieno", b"\x00" * 3072, 0),
                               ("un blob di ZERO byte", b"", 1),
                               ("un vettore NULL", None, 1)):
        with tempfile.TemporaryDirectory() as cartella:
            db = pathlib.Path(cartella) / "finto.db"
            con = sqlite3.connect(db)
            # lo schema con i nomi VERI dello store (proposition, non text):
            # un banco con lo schema inventato prova solo se stesso.
            con.execute("CREATE TABLE facts (id TEXT, proposition TEXT, embedding BLOB, "
                        "embedding_model TEXT, created_at REAL)")
            con.execute("INSERT INTO facts VALUES ('aaaa','un fatto di prova',?,?,?)",
                        (blob, "" if blob == b"" else "modello/x", 1788989746.0))
            con.commit()
            con.close()
            print(f"=== {nome} ===")
            avuto = stampa(misura(db))
            ok = avuto == atteso
            esiti.append(ok)
            print(f"    atteso {atteso}, avuto {avuto}  {'OK' if ok else 'ROSSO'}\n")
    if all(esiti):
        print(f"AUTOTEST VERDE: {len(esiti)} casi su {len(esiti)} — il controllo distingue "
              "«nessun vettore», «vettore vuoto» e «vettore pieno».")
        return 0
    print(f"AUTOTEST ROSSO: {esiti.count(False)} casi sbagliati su {len(esiti)}.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", help="uno store preciso (default: quello di CONFIG)")
    parser.add_argument("--autotest", action="store_true")
    argomenti = parser.parse_args(argv)
    if argomenti.autotest:
        return autotest()
    db = pathlib.Path(argomenti.db) if argomenti.db else db_dello_store()
    if not db.exists():
        print(f"vettori_vuoti.py — nessuno store in {db}: niente da misurare.")
        return 0
    return stampa(misura(db))


if __name__ == "__main__":
    sys.exit(main())
