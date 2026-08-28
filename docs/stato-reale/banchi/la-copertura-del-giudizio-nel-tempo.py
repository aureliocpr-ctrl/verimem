#!/usr/bin/env python
"""Quanta parte del corpus è stata GIUDICATA, e come è cambiata nel tempo.

Nato il 2026-08-28 per una ragione sbagliata: stavo spiegando il «2,2% di fatti
giudicati» che un commento del prodotto cita, e sono andata a controllare che
fosse ancora vero. Non lo era da un mese. Il banco esiste perché quel numero
possa essere **rimisurato invece che citato**.

COSA MISURA, e cosa NO
  `grounding_score` non nullo significa **giudicato**, non **ammesso**: un fatto
  giudicato e quarantinato conta qui come giudicato, ed è giusto — è una
  misura di COPERTURA del giudizio, non di accuratezza. Chi la porta in vetrina
  non la chiami accuratezza.

IL CAVEAT CHE VA LETTO PER PRIMO
  Il volume del corpus è quasi tutto `cli:local`, cioè le istanze che lavorano
  al progetto, e la loro disciplina impone di passare una fonte a ogni
  scrittura. Il moat non gira senza fonte, per costruzione. ⇒ Il numero dice
  «quando la fonte c'è, il giudizio avviene», NON «il prodotto giudica quasi
  tutto ciò che un utente qualunque scrive». Le porte `mcp` e `sdk` hanno
  troppo pochi fatti perché il loro tasso significhi qualcosa, e il banco lo
  stampa apposta: un tasso su 6 casi non è un tasso.

SOLA LETTURA. Apre lo store con ``?mode=ro``: non scrive, non migra, non tocca
nulla. Il percorso lo chiede al prodotto (``CONFIG.semantic_db``) e non lo
indovina — in questa casa esistono due `semantic.db` e quello al percorso ovvio
è vuoto.

    python docs/stato-reale/banchi/la-copertura-del-giudizio-nel-tempo.py
"""
from __future__ import annotations

import sqlite3
import sys
import time
from datetime import datetime, timezone


def _riga(etichetta: str, giudicati: int, totale: int) -> str:
    quota = (100.0 * giudicati / totale) if totale else 0.0
    avviso = "   ⚠️ troppo pochi per un tasso" if 0 < totale < 30 else ""
    return f"  {etichetta:<22} {giudicati:>6} su {totale:>6} = {quota:5.1f}%{avviso}"


def main() -> int:
    from verimem.config import CONFIG

    percorso = str(CONFIG.semantic_db)
    con = sqlite3.connect(f"file:{percorso}?mode=ro", uri=True)

    # Il regime, stampato per primo: la norma di squadra vuole ora e perimetro
    # accanto a ogni numero, perché un conteggio su un corpus che cresce
    # invecchia da solo.
    adesso = datetime.now(timezone.utc).astimezone()
    print(f"store (chiesto al prodotto): {percorso}")
    print(f"istante della misura:        {adesso:%Y-%m-%d %H:%M %Z}")

    totale, giudicati = con.execute(
        "SELECT COUNT(*), SUM(CASE WHEN grounding_score IS NOT NULL THEN 1 ELSE 0 END) "
        "FROM facts"
    ).fetchone()
    print(f"corpus:                      {totale} fatti\n")

    print("COPERTURA COMPLESSIVA")
    print(_riga("tutto il corpus", giudicati or 0, totale))

    print("\nPER FINESTRA TEMPORALE  (la finestra sul conteggio mentirebbe:")
    print("                         mille fatti possono essere un'ora o un mese)")
    ora = time.time()
    for etichetta, giorni in (("ultime 24 ore", 1), ("ultimi 7 giorni", 7),
                              ("ultimi 30 giorni", 30)):
        n, g = con.execute(
            "SELECT COUNT(*), SUM(CASE WHEN grounding_score IS NOT NULL THEN 1 ELSE 0 END) "
            "FROM facts WHERE created_at > ?", (ora - giorni * 86400,)
        ).fetchone()
        print(_riga(etichetta, g or 0, n))

    print("\nPER MESE  (è qui che si vede se è cambiato qualcosa, e quando)")
    for mese, n, g in con.execute(
        "SELECT strftime('%Y-%m', created_at, 'unixepoch'), COUNT(*), "
        "SUM(CASE WHEN grounding_score IS NOT NULL THEN 1 ELSE 0 END) "
        "FROM facts GROUP BY 1 ORDER BY 1 DESC LIMIT 6"
    ):
        print(_riga(mese or "(senza data)", g or 0, n))

    print("\nPER PORTA  (il tasso di una porta con pochi fatti non è un tasso)")
    for chi, n, g in con.execute(
        "SELECT COALESCE(writer_principal, '(nessuna provenienza)'), COUNT(*), "
        "SUM(CASE WHEN grounding_score IS NOT NULL THEN 1 ELSE 0 END) "
        "FROM facts WHERE created_at > ? GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 8",
        (ora - 7 * 86400,)
    ):
        print(_riga(str(chi)[:22], g or 0, n))

    con.close()
    print("\n⚖️  giudicato ≠ ammesso: questa è copertura del giudizio, non accuratezza.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
