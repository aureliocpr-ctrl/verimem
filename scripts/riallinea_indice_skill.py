"""Riallinea l'indice delle skill ai file, che sono la fonte di verità.

IL PREGRESSO DI `5e9dc683`. `SkillLibrary.store` scriveva il JSON, poi
chiamava `embedding.encode` (fallibile), poi l'indice: un encode che non
risponde lasciava il file nuovo e l'indice vecchio. L'ordine è curato, ma le
scritture già andate a metà restano.

Misurato sul corpus vivo: **159 skill su 324** hanno due status, tutte
`file=retired` / `indice=candidate` — è il ritiro a non essere arrivato in
fondo, sempre nella stessa direzione. E `retrieve()` interroga l'INDICE,
quindi la libreria pescava skill morte.

CHI VINCE, e non è una preferenza. `_load_all_skills` fa
`dir.glob("*.json")`: i file sono la fonte del CONTENUTO, l'indice è un
indice — derivato, e ricostruibile da loro. Lo status che il file porta è
anche il più recente, perché è il primo a essere scritto.

Si tocca solo lo `status`: il testo della skill non è cambiato, quindi
l'embedding già nell'indice resta valido e non va ricalcolato — che è poi la
riga da cui è nato tutto.

DRY-RUN DI DEFAULT.

    python scripts/riallinea_indice_skill.py
    python scripts/riallinea_indice_skill.py --apply
"""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DIR = Path.home() / ".engram" / "skills"
#: l'indice sta DENTRO la cartella delle skill, non accanto: la prima stesura
#: lo cercava un livello sopra e diceva «manca» su uno store perfettamente sano.
DB = DIR / "skills_index.db"


def _divergenti(dir_path: Path, con: sqlite3.Connection):
    """(id, stato_file, stato_indice) per ogni skill che non concorda."""
    indice = dict(con.execute("SELECT id, status FROM skills"))
    fuori, orfani = [], []
    for p in sorted(dir_path.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un file illeggibile non è una divergenza
            continue
        sid, sfile = d.get("id"), d.get("status")
        if not sid:
            continue
        if sid not in indice:
            orfani.append((sid, sfile))
        elif indice[sid] != sfile:
            fuori.append((sid, sfile, indice[sid]))
    return fuori, orfani


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dir", default=str(DIR))
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()

    dir_path, db = Path(args.dir), Path(args.db)
    if not dir_path.exists() or not db.exists():
        print(f"manca {dir_path} o {db}")
        return 1

    con = sqlite3.connect(str(db))
    try:
        n_file = len(list(dir_path.glob("*.json")))
        n_idx = con.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        fuori, orfani = _divergenti(dir_path, con)

        print(f"skill: {n_file} file, {n_idx} righe nell'indice")
        print(f"divergenti: {len(fuori)}   solo-file (senza riga): {len(orfani)}")
        versi = collections.Counter((f, i) for _s, f, i in fuori)
        for (sfile, sidx), n in versi.most_common():
            print(f"   {n:4d}  file={sfile}  indice={sidx}")
        for sid, sfile in orfani[:5]:
            print(f"   ORFANA {sid} (file={sfile}) — nessuna riga nell'indice")

        if not fuori:
            print("\nindice allineato")
            return 0
        if not args.apply:
            print("\nDRY-RUN: niente è stato scritto. `--apply` per "
                  "riallineare l'indice ai file.")
            return 0

        con.executemany("UPDATE skills SET status = ? WHERE id = ?",
                        [(f, s) for s, f, _i in fuori])
        con.commit()
        rest, _ = _divergenti(dir_path, con)
        print(f"\nriallineate {len(fuori)} righe; divergenti ora: {len(rest)}")
        if orfani:
            print(f"⚠ le {len(orfani)} solo-file restano: creare la riga vuole "
                  f"l'embedding, cioè la chiamata che ha causato il problema. "
                  f"`scripts/backfill_*` è la via giusta, non questo script.")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
