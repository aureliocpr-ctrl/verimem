"""Porta le MIE celle del registro sopra `origin/main` — per CONTENUTO, non con un rebase.

    python ws7-porta-le-celle-su-main.py <repo> [<tuo-ramo>] [--scrivi]

Senza `--scrivi` non tocca niente: stampa il piano e i controlli. Con `--scrivi`
applica al file di lavoro (che deve essere gia' su un albero fermo a main).

━━ PERCHE' NON IL REBASE, e non e' un'opinione ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`00-ESAME.md` e' un file dove OGNI CELLA E' UNA RIGA sola, lunga migliaia di
caratteri, e ogni commit che aggiorna una cella tocca QUELLA riga. Il 04/09 alle
21:50 ho rebasato 19 commit su main: **8 conflitti a catena, tutti sulla stessa
riga**, e lo script di risoluzione che ho scritto sul momento **ha moltiplicato
le celle: 186 invece di 170**. Il difetto era nel mio controllo, non nel rebase:
cercavo ID duplicati, ma la mia risoluzione RINUMERAVA, quindi un duplicato non
poteva nascere e il controllo non poteva accendersi mai.
⇒ Qui il controllo e' un altro, e PUO' fallire: **ogni cella che sta su main deve
   ricomparire nell'uscita, identica oppure contenuta in una piu' lunga.** Se una
   sparisce o cambia senza contenere l'originale, il programma si ferma.

━━ LE TRE SITUAZIONI, e cosa fa ciascuna ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  (a) stesso ID e la mia CONTIENE quella di main  -> mio aggiornamento: sostituisco
  (b) stesso ID ma testi diversi                  -> due celle diverse hanno preso lo
                                                     stesso numero: **main tiene il suo**,
                                                     la mia va al primo numero libero
  (c) ID solo mio                                 -> in coda, col suo numero se libero
E i riferimenti incrociati (`LANT-174` dentro il testo di un'altra mia cella)
seguono la rinumerazione, altrimenti la cella cita se stessa col nome vecchio.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REG = "docs/stato-reale/00-ESAME.md"
RX = re.compile(r"^\| (LANT-\d+) \|")


def da_git(repo: Path, ref: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{REG}"],
                         capture_output=True, text=True, encoding="utf-8")
    if out.returncode:
        raise SystemExit(f"  git show {ref} fallito: {out.stderr[:200]}")
    return out.stdout.split("\n")


def indicizza(righe: list[str]) -> dict[str, str]:
    return {m.group(1): r for r in righe if (m := RX.match(r))}


def solo_aggiunte(prima: str, dopo: str) -> bool:
    """`dopo` contiene tutto `prima`? — cioe' il diff e' fatto SOLO di inserimenti.

    E' il controllo che deve poter FERMARE questo programma, e va scritto con
    cura perche' ieri il mio controllo non poteva accendersi mai (cercava
    duplicati mentre la mia risoluzione rinumerava).
    Un `startswith` non basta: la coda di una cella la si inserisce PRIMA delle
    ultime colonne, non in fondo alla riga. Ma «non e' un prefisso» non vuol dire
    «ho perso qualcosa»: la domanda giusta e' se dal testo di main all'uscita ci
    sia una sola CANCELLAZIONE. Se il diff e' tutto `equal` + `insert`, nulla di
    cio' che sta su main e' andato perso — e questo lo si prova, non si assume.
    """
    import difflib
    ops = difflib.SequenceMatcher(None, prima, dopo, autojunk=False).get_opcodes()
    return all(tag in ("equal", "insert") for tag, *_ in ops)


def titolo(riga: str) -> str:
    """La DOMANDA della cella — seconda colonna della tabella.

    ⚠️ E' il criterio che distingue «la mia cella aggiornata» da «due celle
    diverse con lo stesso numero», e ci sono arrivata sbagliando DUE volte in
    due giorni, in due direzioni opposte:
      · 04/09: criterio troppo LARGO (rinumerava tutto) -> 186 celle invece di 170;
      · 05/09: criterio troppo STRETTO (`startswith` sull'intera riga) -> chiamava
        collisione anche i miei aggiornamenti, perche' la coda l'avevo inserita
        DENTRO la cella, prima delle ultime colonne, e non appesa in fondo.
    Il criterio giusto e' quello che avevo usato a mano fin dall'inizio: **due
    celle sono la stessa se pongono la stessa domanda**, comunque sia cresciuto
    il resto della riga.
    """
    parti = riga.split(" | ")
    return parti[1].strip() if len(parti) > 1 else riga


def main() -> None:
    repo = Path(sys.argv[1])
    scrivi = "--scrivi" in sys.argv
    ramo = next((a for a in sys.argv[2:] if not a.startswith("--")),
                "ws7/readme-senza-sostegno")

    subprocess.run(["git", "-C", str(repo), "fetch", "origin"], capture_output=True)
    righe_main = da_git(repo, "origin/main")
    celle_main = indicizza(righe_main)
    celle_mie = indicizza((repo / REG).read_text(encoding="utf-8").split("\n")
                          if not scrivi or True else [])
    # ⚠️ quando si scrive, il file di lavoro E' gia' quello di main: le mie celle
    # vanno prese dal ramo, sempre.
    celle_mie = indicizza(da_git(repo, ramo))

    libero = max(int(c.split("-")[1]) for c in celle_main)
    aggiorna: dict[str, str] = {}
    aggiungi: list[tuple[str, str]] = []
    rinomina: dict[str, str] = {}

    for cid, mia in celle_mie.items():
        sul_main = celle_main.get(cid)
        if sul_main is None:
            aggiungi.append((cid, mia))
            print(f"  (c) {cid}: solo mia -> in coda col suo numero")
        elif mia == sul_main:
            pass
        elif titolo(mia) == titolo(sul_main):
            aggiorna[cid] = mia
            print(f"  (a) {cid}: mio aggiornamento (+{len(mia)-len(sul_main)} char) -> sostituisco")
        else:
            libero += 1
            nuovo = f"LANT-{libero}"
            rinomina[cid] = nuovo
            aggiungi.append((nuovo, f"| {nuovo} |" + mia[len(f"| {cid} |"):]))
            print(f"  (b) {cid}: COLLISIONE (main = «{sul_main[14:70].strip()}…») "
                  f"-> la mia diventa {nuovo}")

    # i riferimenti incrociati seguono la rinumerazione, ma SOLO dentro le mie celle
    if rinomina:
        for i, (cid, testo) in enumerate(aggiungi):
            for vecchio, nuovo in rinomina.items():
                testo = re.sub(rf"\b{vecchio}\b(?!\s*\|)", nuovo, testo) \
                    if not testo.startswith(f"| {vecchio} |") else testo
            aggiungi[i] = (cid, testo)
        print(f"  riferimenti incrociati aggiornati: {rinomina}")

    fuori: list[str] = []
    for r in righe_main:
        m = RX.match(r)
        fuori.append(aggiorna.get(m.group(1), r) if m else r)
    # le nuove vanno dopo l'ULTIMA riga di cella
    ultimo = max(i for i, r in enumerate(fuori) if RX.match(r))
    for k, (_, testo) in enumerate(aggiungi, 1):
        fuori.insert(ultimo + k, testo)

    # ━━ IL CONTROLLO CHE PUO' FALLIRE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    finali = indicizza(fuori)
    persi = [c for c, t in celle_main.items()
             if c not in finali or not solo_aggiunte(t, finali[c])]
    ids = [m.group(1) for r in fuori if (m := RX.match(r))]
    dupl = sorted({c for c in ids if ids.count(c) > 1})
    print()
    print(f"  celle su main {len(celle_main)} · mie {len(celle_mie)} · uscita {len(finali)}")
    print(f"  celle di main PERSE o alterate: {persi or 'nessuna'}")
    print(f"  ID duplicati: {dupl or 'nessuno'}")
    attese = len(celle_main) + len(aggiungi)
    print(f"  conto atteso {attese} · trovato {len(finali)} · "
          f"{'OK' if attese == len(finali) else 'DISCORDE'}")
    if persi or dupl or attese != len(finali):
        raise SystemExit("  ⛔ il controllo si e' acceso: NON scrivo.")

    if scrivi:
        (repo / REG).write_text("\n".join(fuori), encoding="utf-8")
        print(f"\n  scritto {REG}")
    else:
        print("\n  (prova a vuoto: nessun file toccato — aggiungi --scrivi)")


if __name__ == "__main__":
    main()
