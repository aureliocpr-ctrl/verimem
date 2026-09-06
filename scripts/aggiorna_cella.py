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
    senza toccare nulla invece di duplicarlo;
  · 🔑 **e l'albero in cui si scrive**: le quattro garanzie qui sopra sono
    tutte sul CONTENUTO della riga, e per mesi nessuna ha detto DOVE finiva.
    Chi lavorava in un worktree scriveva nell'albero dello script con
    `RC = 0` (misurato da @ws5 il 06/09). Adesso: `--repo` decide, e senza
    `--repo` la radice git della cartella corrente deve coincidere con
    quella dello script, **altrimenti ci si ferma nominando i due percorsi**.
    E la riga di esito dice **dove ha scritto anche quando non sbaglia**.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
REGISTRO = RADICE / "docs" / "stato-reale" / "00-ESAME.md"


def _radice_del_chiamante() -> Path | None:
    """La radice git della cwd, o None se la cwd non e' dentro un repo.

    Si DERIVA, non si assume: in un worktree `--show-toplevel` da la radice
    del worktree, che e' esattamente l'albero che vogliamo distinguere da
    quello dove sta questo file.
    """
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=30)
    except Exception:  # noqa: BLE001 — git assente o non eseguibile
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return Path(out.stdout.strip()).resolve()


def scegli_registro(repo: Path | None) -> Path | None:
    """Decide in quale albero si scrive, e si RIFIUTA se non e' chiaro.

    🔴 06/09 07:12 — @ws5 Tara ha misurato il difetto: eseguito con la cwd in
    un worktree, questo script scriveva nell'albero **dove sta il file** e
    stampava `RC = 0`. Non sbagliava il contenuto: sbagliava l'albero, ed e'
    peggio, perche' il contenuto era giusto e quindi nessuno se ne accorgeva.
    Il suo RED: `PRIMA finto=154e1f06 ... DOPO finto=c2681000`, con worktree e
    condiviso **invariati**.

    ⇒ 🔑 **Il docstring di questo file dichiara quattro GARANZIE e sono tutte
      sul CONTENUTO della riga: nessuna su DOVE finisce.** Questa e' la quinta.

    Regola: `--repo` vince quando c'e'; senza, la radice del chiamante deve
    coincidere con quella dello script, altrimenti ci si ferma NOMINANDO I DUE
    PERCORSI — un errore che dice «sono due» e li mostra si ripara in dieci
    secondi, un `RC = 0` sbagliato costa la giornata di chi lo legge.
    """
    if repo is not None:
        radice = repo.resolve()
        if not (radice / "docs" / "stato-reale").is_dir():
            print(f"  --repo {radice} non ha docs/stato-reale/: mi fermo")
            return None
        return radice / "docs" / "stato-reale" / "00-ESAME.md"

    chiamante = _radice_del_chiamante()
    if chiamante is None:
        print("  la cartella corrente non e' dentro un repo git, quindi non so")
        print("     in quale albero vuoi scrivere. Passa --repo <percorso>.")
        print(f"     (l'albero di questo script sarebbe: {RADICE})")
        return None
    if chiamante != RADICE:
        print("  DUE ALBERI DIVERSI, e non indovino quale intendi:")
        print(f"     dove lavori tu (radice git della cwd) : {chiamante}")
        print(f"     dove sta questo script                : {RADICE}")
        print("     Scegli: --repo <percorso>. Senza, scriverei nell'albero")
        print("     dello script e il TUO registro resterebbe invariato.")
        return None
    return REGISTRO
#: separa su una barra NON preceduta da backslash (`LANT-132`)
COLONNE = re.compile(r"(?<!\\)\|")
#: la colonna del verdetto, contando dalla stringa vuota iniziale
VERDETTO = 6


def inserisci(dopo: str, riga_nuova: Path, registro: Path) -> int:
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
    righe = registro.read_text(encoding="utf-8").splitlines(keepends=True)
    if any(r.startswith(f"| {ident} |") for r in righe):
        print(f"  {ident} esiste gia' nel registro: non lo duplico")
        return 1
    trovate = [k for k, r in enumerate(righe) if r.startswith(f"| {dopo} |")]
    if len(trovate) != 1:
        print(f"  {len(trovate)} righe per {dopo}: mi fermo")
        return 1
    righe.insert(trovate[0] + 1, testo + "\n")
    registro.write_text("".join(righe), encoding="utf-8")
    print(f"  {ident} inserita dopo {dopo} · {len(testo)} char · "
          f"{n_col} colonne · chiude con la barra")
    print(f"     scritto in: {registro}")
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
    # 🔑 02/09 02:55 — CONTROFIRMARE COSTAVA PIU' DI QUANTO VALESSE.
    # @ws2 ha misurato che il contratto e' allo 0,4% (3 celle su 781 ne hanno
    # due) e che 67 delle 78 esistenti sono sue. Ho cercato le controfirme
    # «nella sostanza ma non nella forma» — il registro ne documenta almeno una
    # che «il contatore non vedeva» — e NON sono riuscita a trovarle: col
    # criterio largo 404 candidate su 652 celle, con quello stretto 42, e le
    # prime TRE lette erano tutte falsi positivi. ⇒ Il numero di @ws2 non va
    # corretto: e' un tasso su un MARCATORE, ed e' il migliore disponibile
    # proprio perche' il marcatore e' esplicito.
    # ⇒ La cura non e' un contatore piu' furbo, e' ABBASSARE L'ATTRITO: se la
    #   forma canonica costa un'opzione, si usa; se costa ricordarsela e
    #   scriverla a mano, si perde. «L'adozione misura l'attrito, non la
    #   disciplina» (retract 64/64 contro 1/15).
    # ⚠️ E l'ora la mette il SISTEMA, non le dita: cinque derive su cinque, nel
    #   registro, erano numeri digitati (la stessa ragione di prossima_cella.py).
    ap.add_argument("--controfirma", metavar="TESTO",
                    help="appende al verdetto una controfirma nella FORMA "
                         "CANONICA (la parola che il contatore cerca), con "
                         "data e ora lette dal sistema. Il TESTO deve dire "
                         "COSA hai rifatto e COSA hai trovato")
    ap.add_argument("--come", default=os.environ.get("VERIMEM_AGENT", ""),
                    help="la tua sigla (default: $VERIMEM_AGENT)")
    ap.add_argument("--repo", type=Path, default=None, metavar="PERCORSO",
                    help="l'albero in cui scrivere. Senza, si usa quello di "
                         "questo script SOLO se coincide con la radice git "
                         "della cartella corrente; se differiscono ci si "
                         "ferma nominando i due percorsi")
    a = ap.parse_args()

    modi = [bool(a.coda), bool(a.inserisci_dopo), bool(a.controfirma)]
    if sum(modi) != 1:
        print("  serve esattamente uno fra --coda, --inserisci-dopo "
              "e --controfirma")
        return 1
    registro = scegli_registro(a.repo)
    if registro is None:
        return 1

    if a.inserisci_dopo:
        return inserisci(a.cella, a.inserisci_dopo, registro)

    if a.controfirma:
        if not a.come:
            print("  serve --come <sigla>, oppure VERIMEM_AGENT nell'ambiente:")
            print("     una controfirma senza autore non e' una controfirma.")
            return 1
        quando = datetime.now().strftime("%d/%m %H:%M")
        testo = (f"✅ **CONTROFIRMATA da {a.come} il {quando}** "
                 f"(ora dal sistema) — {a.controfirma}")
    else:
        testo = a.coda.read_text(encoding="utf-8").strip()
    righe = registro.read_text(encoding="utf-8").splitlines(keepends=True)
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
    registro.write_text("".join(righe), encoding="utf-8")
    print(f"  {a.cella}: {len(riga)} -> {len(nuova)} char · "
          f"{len(col)} colonne invariate · chiude con la barra")
    print(f"     scritto in: {registro}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
