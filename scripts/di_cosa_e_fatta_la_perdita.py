"""Di che cosa è fatta la perdita del 21%, per CAUSA — e quale pezzo è curabile.

`quanti_fatti_sono_davvero_serviti.py` dà il numero giusto alla domanda giusta:
quanti fatti, di quelli scritti, tornano davvero a chi li chiede. Il 21% che
stampa è vero. Ma è una SOMMA, e chi lo legge come un solo difetto sbaglia
bersaglio: sul corpus di casa il pezzo più grosso sono i checkpoint di sessione
di un hook, potati di proposito.

MISURATO il 2026-09-09 su `~/.engram` (18.098 fatti scritti)::

    autohook-snapshot         1463     8.1%   potatura VOLUTA (non è perdita)
    quarantenati vivi         1406     7.8%   il moat che fa il suo mestiere
    same-source evolution      558     3.1%   <- la perdita curabile
    exact-text dedup           202     1.1%   testo identico (perdita zero)
    heal_contradictions        206     1.1%   il perdente di un clash
                                     -----
                                      21.2%

⚠️ PERCHÉ QUESTO SCRIPT ESISTE. Il contratto del rilascio chiede «21% → ≤ 2%».
Con questa scomposizione si vede che il bersaglio non è raggiungibile dalla
cura che gli è assegnata (versionare invece di ritirare muove al massimo
3,1 + 1,1 = 4,2 punti) e che per arrivare a 2 bisognerebbe rimettere in circolo
i quarantenati e gli snapshot — **peggiorare il prodotto per migliorare il
numero**. Il docstring dello script gemello racconta lo stesso errore già
commesso una volta: «la cura non salvava un solo fatto — cambiava il NOME della
perdita, da "ritirato" a "quarantinato"».

🔑 CONTROLLO POSITIVO, in coda e non aggirabile: la somma delle cause deve
fare la perdita totale. Se una causa nuova comparisse (un ritiro con una
ragione che questo script non conosce), il numero non tornerebbe e lo script
esce con 1 invece di stampare una tabella rassicurante. Un righello che non
può accorgersi di ciò che non conosce non è un righello.

🪞 E LA PRIMA STESURA DI QUEL CONTROLLO NON POTEVA ACCENDERSI — trovato in
revisione dal ruolo QA. `altre` era derivata per differenza
(`ritirati - contate`), quindi la verifica era l'identità
`contate + (ritirati - contate) == ritirati`: vera per costruzione, su
qualunque database, anche rotto. Ora `altre` si CONTA con una query che
esclude le cause note, e i due lati arrivano da due interrogazioni
indipendenti: una ragione che ricadesse sotto due pattern verrebbe contata
due volte a sinistra e una sola a destra, e il righello lo direbbe.
⇒ **In uno script che esiste per dire «questo numero non misura ciò che
credi», il controllo che non può fallire era la stessa forma, un piano più
sotto.**

USO::

    python scripts/di_cosa_e_fatta_la_perdita.py <data_dir>
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys

#: Le cause note, in ordine di grandezza sul corpus di casa. La chiave è il
#: prefisso di `superseded_reason` scritto da chi ritira; il testo dice se
#: quella riga è una perdita per l'utente o igiene voluta.
CAUSE: list[tuple[str, str, str]] = [
    ("autohook-snapshot", "autohook-snapshot%",
     "potatura VOLUTA dei checkpoint di sessione (non è memoria dell'utente)"),
    ("same-source evolution", "same-source evolution%",
     "il write path ritira il precedente: LA PERDITA CURABILE"),
    ("heal_contradictions", "heal_contradictions%",
     "il perdente di un clash numerico o booleano"),
    ("exact-text dedup", "exact-text dedup%",
     "testo byte-identico: perdita informativa zero"),
]


def scomponi(db: pathlib.Path) -> dict:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    uno = lambda sql, *a: con.execute(sql, a).fetchone()[0]  # noqa: E731

    scritti = uno("SELECT COUNT(*) FROM facts")
    ritirati = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL")
    quarantenati = uno(
        "SELECT COUNT(*) FROM facts "
        "WHERE superseded_by IS NULL AND status = 'quarantined'")

    per_causa: list[tuple[str, int, str]] = []
    contate = 0
    for nome, like, nota in CAUSE:
        n = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL "
                "AND superseded_reason LIKE ?", like)
        per_causa.append((nome, n, nota))
        contate += n
    # ⚠️ `altre` si CONTA, non si deriva per differenza. Con
    # `altre = ritirati - contate` il controllo in coda diventava l'identità
    # `contate + (ritirati - contate) == ritirati`, vera per costruzione: un
    # controllo che non può accendersi. Qui la riga si conta escludendo le
    # cause note, così i due numeri arrivano da due query indipendenti e la
    # verifica ha qualcosa da verificare — per esempio una ragione che ricade
    # sotto DUE pattern, che sarebbe contata due volte a sinistra e una sola
    # a destra.
    esclusioni = " ".join("AND superseded_reason NOT LIKE ?" for _ in CAUSE)
    altre = uno(
        "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL "
        "AND (superseded_reason IS NULL OR (1=1 " + esclusioni + "))",
        *[like for _, like, _ in CAUSE])
    con.close()
    return {
        "scritti": scritti, "ritirati": ritirati,
        "quarantenati": quarantenati, "per_causa": per_causa,
        "altre": altre, "perdita": ritirati + quarantenati,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("data_dir", help="la data dir (contiene semantic/semantic.db)")
    a = p.parse_args(argv)

    base = pathlib.Path(a.data_dir)
    db = base / "semantic" / "semantic.db"
    if not db.exists():
        db = base if base.suffix == ".db" else db
    if not db.exists():
        print(f"database non trovato: {db}", file=sys.stderr)
        return 2

    d = scomponi(db)
    scritti = d["scritti"] or 1
    print(f"  scritti  {d['scritti']}\n")
    print("  LA PERDITA, per causa")
    for nome, n, nota in d["per_causa"]:
        print(f"    {nome:<24} {n:>6}  {n * 100 / scritti:>5.1f}%   {nota}")
    print(f"    {'quarantenati vivi':<24} {d['quarantenati']:>6}"
          f"  {d['quarantenati'] * 100 / scritti:>5.1f}%"
          f"   il moat: «kept OUT of default recall» è la promessa")
    if d["altre"]:
        print(f"    {'ALTRE (sconosciute)':<24} {d['altre']:>6}"
              f"  {d['altre'] * 100 / scritti:>5.1f}%   ragioni non censite qui")
    print(f"    {'':<24} {'-' * 6}")
    print(f"    {'perdita totale':<24} {d['perdita']:>6}"
          f"  {d['perdita'] * 100 / scritti:>5.1f}%")

    curabile = next(n for nome, n, _ in d["per_causa"]
                    if nome == "same-source evolution")
    clash = next(n for nome, n, _ in d["per_causa"]
                 if nome == "heal_contradictions")
    print(f"\n  CURABILE VERSIONANDO      {curabile + clash:>6}"
          f"  {(curabile + clash) * 100 / scritti:>5.1f}%"
          f"   (same-source evolution + clash)")
    print(f"  ⇒ una cura perfetta porta la perdita a"
          f" {(d['perdita'] - curabile - clash) * 100 / scritti:.1f}%,"
          f" non a 2%: il resto è igiene voluta e il moat.")

    # CONTROLLO POSITIVO: le cause devono spiegare TUTTI i ritiri. Se domani
    # comparisse un ritiro con una ragione che questo script non conosce, la
    # tabella sopra sarebbe rassicurante e falsa.
    contate = sum(n for _, n, _ in d["per_causa"])
    if contate + d["altre"] != d["ritirati"]:
        print("\n  🔴 il conto non torna: le cause non spiegano i ritiri",
              file=sys.stderr)
        return 1
    if d["altre"] > d["ritirati"] * 0.05:
        print(f"\n  🔴 {d['altre']} ritiri ({d['altre'] * 100 / d['ritirati']:.1f}%)"
              f" hanno una ragione che questo script non conosce:"
              f" censiscila prima di fidarti della tabella", file=sys.stderr)
        return 1
    print("\n  ✅ le cause note spiegano i ritiri"
          f" ({d['ritirati'] - d['altre']}/{d['ritirati']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
