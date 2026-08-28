"""QUANTI QUARANTINATI SONO **IN BANDA** E NON SOTTO IL CUT — la causa su scala.

W7-42 ha chiuso il fronte degli scambi: non c'e' una variabile del testo, c'e'
la **banda [40, 80]** (`cut=40`, `tau_hi=80`, `band_enforced=True`). Un fatto il
cui punteggio cade **in mezzo** non viene ne' ammesso ne' rifiutato: viene
**trattenuto in attesa di un'escalation** — quella che, secondo W7-26, gira con
`claude -p` **senza `--model`**.

⇒ La domanda che decide se quel risultato e' un caso di laboratorio o la
struttura della coda: **quanti dei quarantinati vivi hanno un punteggio DENTRO
la banda invece che sotto il cut?**

· **sotto 40** = il moat li ha giudicati non sostenuti. **Il gate ha fatto il suo
  lavoro**, e riammetterli sarebbe un errore.
· **in [40, 80]** = **il gate NON ha deciso**. Sono in attesa di un giudizio che
  non e' arrivato. ⇒ E' su questi che una band escalation funzionante cambierebbe
  l'esito, e sono la popolazione su cui «versionare invece di ritirare» ha senso.
· **sopra 80** = quarantinati da ALTRO (un layer lessicale), col moat che li
  approvava: e' il caso `withheld_despite_judge`.

CONTROLLI CHE POSSONO FALLIRE:
 (1) se `grounding_score` e' NULL su quasi tutti, questa misura non dice niente
     sulla banda: lo dico e NON pubblico una percentuale calcolata su un
     denominatore che non e' quello che sembra.
 (2) DUE denominatori dichiarati: sul totale dei quarantinati e sui soli
     giudicati. La stessa quota letta sui due da' numeri diversi, e citarne uno
     solo e' il modo classico di ingannare senza mentire.

    python -u docs/stato-reale/banchi/quanti-quarantinati-sono-IN-BANDA-e-non-sotto-il-cut.py
"""

from __future__ import annotations

import sqlite3
import sys


def main() -> int:
    try:
        from verimem.config import CONFIG
        from verimem.grounding_gate import (
            _ce_band_tau_hi,
            resolve_write_threshold_for,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    CUT = resolve_write_threshold_for("local")
    TAU = _ce_band_tau_hi()
    print(f"  db: {CONFIG.semantic_db}")
    print(f"  banda letta dal gate: [{CUT}, {TAU}]")

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = list(con.execute(
        "SELECT grounding_score, quarantined_by FROM facts "
        "WHERE status='quarantined' AND superseded_by IS NULL"))
    n = len(righe)
    print(f"  quarantinati vivi: {n}")
    if not n:
        print("  NON RIUSCITO: nessuna riga.")
        return 1

    senza = [q for s, q in righe if s is None]
    con_punteggio = [(s, q) for s, q in righe if s is not None]
    m = len(con_punteggio)
    print(f"  di cui SENZA grounding_score: {len(senza)}"
          f"   ({100.0 * len(senza) / n:.1f}%)")
    print(f"  di cui giudicati            : {m}"
          f"   ({100.0 * m / n:.1f}%)")

    print("\n  -- CONTROLLO (1): la misura ha un oggetto?")
    if m < 0.1 * n:
        print(f"     CADUTO - solo {m} righe su {n} hanno un punteggio: questa")
        print("     misura non dice niente sulla banda, e non pubblico una")
        print("     percentuale che sembrerebbe parlare di tutti.")
        return 1
    print(f"     retto - {m} righe giudicate su {n}")

    sotto = [(s, q) for s, q in con_punteggio if s < CUT]
    dentro = [(s, q) for s, q in con_punteggio if CUT <= s < TAU]
    sopra = [(s, q) for s, q in con_punteggio if s >= TAU]

    print("\n  == DOVE CADONO, e i DUE denominatori (controllo 2)")
    print(f"     {'fascia':<22}{'n':>6}   {'su giudicati':>13}   {'su TUTTI':>10}")
    for nome, v in (("sotto il cut (<40)", sotto),
                    ("IN BANDA [40, 80)", dentro),
                    ("sopra tau_hi (>=80)", sopra)):
        print(f"     {nome:<22}{len(v):>6}   {100.0 * len(v) / m:>12.1f}%"
              f"   {100.0 * len(v) / n:>9.1f}%")

    print("\n  == COSA SIGNIFICANO, una per una")
    print(f"     sotto il cut  : il moat li ha giudicati NON sostenuti. Il gate")
    print(f"                     ha fatto il suo lavoro: {len(sotto)} righe.")
    print(f"     IN BANDA      : il gate NON HA DECISO. {len(dentro)} righe")
    print(f"                     aspettano un giudizio che non e' arrivato.")
    print(f"     sopra tau_hi  : il moat li APPROVAVA e sono trattenuti da")
    print(f"                     altro: {len(sopra)} righe (withheld_despite_judge).")

    if sopra:
        print("\n  == CHI li ferma, per i sopra-soglia")
        import collections
        d = collections.Counter((q or "<VUOTA>") for _s, q in sopra)
        for k, v in d.most_common(6):
            print(f"     {v:>5}  {k}")

    print("\n  -- LA RIGA CHE CONTA")
    if dentro:
        print(f"     {len(dentro)} fatti sono in banda: NON sono stati giudicati")
        print("     insostenibili, sono rimasti senza verdetto. ⇒ Su questi una")
        print("     band escalation che consegna cambierebbe l'esito, e sono la")
        print("     popolazione su cui «versionare invece di ritirare» ha senso.")
    else:
        print("     Nessun fatto in banda: il fenomeno di W7-42 non ha")
        print("     rappresentanza in questa coda, ed e' un caso di laboratorio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
