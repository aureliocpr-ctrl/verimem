"""Quanti fatti, di quelli scritti, tornano davvero a chi li chiede.

NASCE DA UN ERRORE MIO, il 2026-08-04, e serve a non ripeterlo. Avevo misurato
una cura contando::

    SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL

e annunciato «da 1 vivo su 25 a 25 su 25, difetto chiuso». Era falso. Un fatto
può sparire in DUE modi e ne guardavo uno solo:

    banco                 scritti   non-superseduti   DAVVERO SERVITI
    prima della cura         25           25                 1
    con la cura              26           26                 1

Nel database, con la cura: ``quarantined`` 25, ``model_claim`` 1. La cura non
salvava un solo fatto — cambiava il NOME della perdita, da «ritirato» a
«quarantinato». Per chi legge la memoria è la stessa cosa: non torna.

⚠️ `superseded_by IS NULL` **non** vuol dire «il fatto è vivo». Vuol dire «non è
stato ritirato», che è un'altra domanda. Il banco aveva risposto con precisione
a una domanda che non era quella che volevo fare.

USO::

    python scripts/quanti_fatti_sono_davvero_serviti.py <data_dir> [--topic X]

Stampa i tre numeri che contano — scritti, non-superseduti, serviti — e la
composizione della perdita. Un solo numero non basta: è proprio il numero solo
che mi ha ingannata.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sqlite3
import sys

#: Gli stati che NON tornano da un recall ordinario. `quarantined` è quello che
#: mi è sfuggito: il fatto è nel database, non è superseduto, e non lo vedrai.
STATI_MUTI = ("quarantined",)


def conta(db: pathlib.Path, topic: str | None = None) -> dict:
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    dove = "WHERE topic = ?" if topic else ""
    par = (topic,) if topic else ()
    q = f"SELECT status, superseded_by FROM facts {dove}"
    righe = con.execute(q, par).fetchall()
    scritti = len(righe)
    non_sup = [r for r in righe if r["superseded_by"] is None]
    serviti = [r for r in non_sup if (r["status"] or "") not in STATI_MUTI]
    per_stato = collections.Counter((r["status"] or "?") for r in non_sup)
    return {
        "scritti": scritti,
        "non_superseduti": len(non_sup),
        "serviti": len(serviti),
        "ritirati": scritti - len(non_sup),
        "muti": len(non_sup) - len(serviti),
        "per_stato": per_stato,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("data_dir", help="la data dir (contiene semantic/semantic.db)")
    p.add_argument("--topic", default=None, help="restringe a un topic")
    a = p.parse_args(argv)

    base = pathlib.Path(a.data_dir)
    db = base / "semantic" / "semantic.db"
    if not db.exists():
        db = base if base.suffix == ".db" else db
    if not db.exists():
        print(f"database non trovato: {db}", file=sys.stderr)
        return 2

    d = conta(db, a.topic)
    print(f"  scritti            {d['scritti']:>6}")
    print(f"  non superseduti    {d['non_superseduti']:>6}"
          f"   (ritirati: {d['ritirati']})")
    print(f"  DAVVERO SERVITI    {d['serviti']:>6}"
          f"   (muti perche' {'/'.join(STATI_MUTI)}: {d['muti']})")
    if d["scritti"]:
        perse = d["scritti"] - d["serviti"]
        print(f"  perdita totale     {perse:>6}"
              f"   ({perse * 100 // d['scritti']}% di cio' che e' stato scritto)")
    if d["per_stato"]:
        print("\n  composizione dei non-superseduti:")
        for st, n in d["per_stato"].most_common():
            muto = "  <- non torna dal recall" if st in STATI_MUTI else ""
            print(f"     {st:<20} {n:>5}{muto}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
