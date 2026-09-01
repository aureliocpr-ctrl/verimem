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


def inserisci(dopo: str, riga_nuova: Path) -> int:
    """Inserisce una cella NUOVA subito dopo `dopo`.

    🔴 31/08 03:32 — AGGIUNTO PERCHE' LO STRUMENTO COPRIVA META' DEL BISOGNO.
    `--coda` curava l'aggiornamento, ma la cella NUOVA la inserivo ancora a
    mano; e «a mano» ha voluto dire heredoc, e heredoc ha mangiato il
    backslash del lookbehind **per la quinta volta stanotte**.
    ⇒ 🔑 **Uno strumento che copre meta' del caso reale lascia in piedi meta'
    del difetto** — e la meta' scoperta e' quella che si usa sotto pressione.
    """
    testo = riga_nuova.read_text(encoding="utf-8").rstrip("\n")
    if not (testo.startswith("| ") and testo.endswith("|")):
        print("  la riga nuova non comincia e non finisce con la barra: mi fermo")
        return 1
    n_col = len(COLONNE.split(testo))
    #: stessa correzione di sotto: il minimo è STRUTTURALE (serve la colonna
    #: del verdetto), non un numero preso dalla famiglia più comune.
    if n_col <= VERDETTO:
        print(f"  la riga nuova ha {n_col} colonne "
              f"(ne serve almeno {VERDETTO + 1}): mi fermo")
        return 1
    ident = testo.split("|")[1].strip()
    righe = REGISTRO.read_text(encoding="utf-8").splitlines(keepends=True)
    if any(r.startswith(f"| {ident} |") for r in righe):
        print(f"  {ident} esiste gia' nel registro: non lo duplico")
        return 1
    trovate = [k for k, r in enumerate(righe) if r.startswith(f"| {dopo} |")]
    if len(trovate) != 1:
        print(f"  {len(trovate)} righe per {dopo}: mi fermo")
        return 1
    righe.insert(trovate[0] + 1, testo + "\n")
    REGISTRO.write_text("".join(righe), encoding="utf-8")
    print(f"  {ident} inserita dopo {dopo} · {len(testo)} char · "
          f"{n_col} colonne · chiude con la barra")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cella", help="es. LANT-130 (o la cella DOPO cui inserire)")
    ap.add_argument("--coda", type=Path,
                    help="file col testo da appendere al verdetto")
    ap.add_argument("--inserisci-dopo", type=Path, metavar="RIGA",
                    help="file con una riga-cella COMPLETA da inserire "
                         "subito dopo `cella`")
    ap.add_argument("--se-manca", default=None,
                    help="non fare niente se la riga contiene gia' questa stringa")
    a = ap.parse_args()

    if bool(a.coda) == bool(a.inserisci_dopo):
        print("  serve esattamente uno fra --coda e --inserisci-dopo")
        return 1
    if a.inserisci_dopo:
        return inserisci(a.cella, a.inserisci_dopo)

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

    # 🔴🪞 01/09 19:49 — LA GUARDIA CHE MANCAVA, e me l'ha insegnata un difetto
    # MIO: il 31/08 ho appeso a `LANT-130` un testo che conteneva un pipe NUDO,
    # e la cella si e' spezzata in due colonne — la sua colonna autrice non si
    # leggeva piu'. **Quella cella era LOAD-BEARING**: la legge Aurelio.
    # ⇒ Il controllo sull'invarianza delle colonne (piu' sotto) NON bastava:
    #   conta con `COLONNE`, che ha il lookbehind e **non vede gli escape**, e
    #   contava solo cio' che il MIO righello vede. Il markdown conta i pipe
    #   NUDI. **Una guardia che misura col proprio righello non protegge da chi
    #   legge con un altro.**
    # ⇒ Qui si rifiuta il testo PRIMA di toccare il file, e la cura non e' un
    #   escape: e' non usare il carattere. Venti minuti dopo aver riparato
    #   `LANT-130` stavo per rifarlo — quindi non e' disciplina, e' lo
    #   strumento che deve dire di no.
    if "|" in testo:
        nudi = testo.count("|") - testo.count("\\|")
        print(f"  il testo da appendere contiene {testo.count('|')} barre "
              f"({nudi} NUDE): spezzerebbero la cella. NON tocco niente.")
        print("     Riformula senza il carattere — un escape NON basta: il")
        print("     markdown lo rende, ma gli altri script contano i pipe nudi.")
        return 1

    col = COLONNE.split(riga)
    # 🔴 31/08 08:22 — TOLTA LA SOGLIA FISSA «>= 10 colonne», su misura di
    # @ws4: `LANT-34` ha 10 pipe e `LANT-109` ne ha 9 — **il numero di colonne
    # varia ANCHE DENTRO LA STESSA FAMIGLIA**, quindi «le W7 ne hanno 9 e le
    # LANT 10» era falso pure quello. Questo strumento avrebbe RIFIUTATO di
    # aggiornare `LANT-109`, e per una ragione inventata da me.
    # ⇒ 🔑 **La guardia giusta non è un numero: è che il numero NON CAMBI
    #   rispetto alla riga che sto toccando** — ed è il controllo che c'era
    #   già dieci righe più sotto. Resta il minimo strutturale (serve almeno
    #   la colonna del verdetto) e la barra finale.
    if len(col) <= VERDETTO or not riga.rstrip().endswith("|"):
        print(f"  {a.cella} ha {len(col)} colonne (ne serve almeno "
              f"{VERDETTO + 1}) e finisce con barra="
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
