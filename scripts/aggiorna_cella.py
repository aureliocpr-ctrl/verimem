"""Aggiunge testo alla colonna VERDETTO di una cella del registro, senza romperla.

    python scripts/aggiorna_cella.py LANT-130 --coda <file.md>
    python scripts/aggiorna_cella.py LANT-130 --coda <file.md> --se-manca "02:45"

PERCHE' ESISTE. Aggiornare una cella significa: leggere la riga, separare le
colonne, appendere in coda al verdetto, riscrivere. Ho scritto quello snippet
**a mano cinque volte in un'ora**, sempre per heredoc, e:

  · il lookbehind `(?<!` backslash `)` passato per heredoc arriva con **un
    backslash solo** e il regex non compila — **quattro volte stanotte**, e la
    quarta e' arrivata **due minuti dopo aver scritto la cella su questo
    difetto** (`LANT-132`);
  · ogni copia rischia una separazione diversa dalle altre — ed e' esattamente
    la classe ① («una copia invece della superficie unica») che ho gia' pagato
    con `ws7_stato.py` contro `conta_celle_esame.py` (`LANT-129`).

⇒ 🔑 **Una lezione scritta non impedisce la ripetizione; uno strumento si'.**
E' lo stesso principio di `posta.py` e `prossima_cella.py`.

GARANZIE, e devono poter fallire:
  · le colonne si separano su una barra **non preceduta da backslash**;
  · la riga deve avere almeno 10 colonne PRIMA e **lo stesso numero DOPO**;
  · la riga deve finire con la barra, prima e dopo;
  · `--se-manca` rende l'operazione idempotente: se il testo c'e' gia', esce
    senza toccare nulla invece di duplicarlo.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
REGISTRO = RADICE / "docs" / "stato-reale" / "00-ESAME.md"
#: separa su una barra NON preceduta da backslash (`LANT-132`)
COLONNE = re.compile(r"(?<!\\)\|")
#: la colonna del verdetto, contando dalla stringa vuota iniziale
VERDETTO = 6


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cella", help="es. LANT-130")
    ap.add_argument("--coda", required=True, type=Path,
                    help="file col testo da appendere al verdetto")
    ap.add_argument("--se-manca", default=None,
                    help="non fare niente se la riga contiene gia' questa stringa")
    a = ap.parse_args()

    testo = a.coda.read_text(encoding="utf-8").strip()
    righe = REGISTRO.read_text(encoding="utf-8").splitlines(keepends=True)
    trovate = [k for k, r in enumerate(righe) if r.startswith(f"| {a.cella} |")]
    if len(trovate) != 1:
        print(f"  {len(trovate)} righe per {a.cella}: mi fermo")
        return 1
    i = trovate[0]
    riga = righe[i].rstrip("\n")

    if a.se_manca and a.se_manca in riga:
        print(f"  {a.cella} contiene gia' '{a.se_manca}': non tocco niente")
        return 0

    col = COLONNE.split(riga)
    if len(col) < 10 or not riga.rstrip().endswith("|"):
        print(f"  {a.cella} ha {len(col)} colonne e finisce con barra="
              f"{riga.rstrip().endswith('|')}: NON la tocco")
        return 1

    col[VERDETTO] = col[VERDETTO].rstrip() + " " + testo + " "
    nuova = "|".join(col)
    if len(COLONNE.split(nuova)) != len(col) or not nuova.endswith("|"):
        print("  la riga nuova non ha la stessa forma: annullo")
        return 1

    righe[i] = nuova + "\n"
    REGISTRO.write_text("".join(righe), encoding="utf-8")
    print(f"  {a.cella}: {len(riga)} -> {len(nuova)} char · "
          f"{len(col)} colonne invariate · chiude con la barra")
    return 0


if __name__ == "__main__":
    sys.exit(main())
