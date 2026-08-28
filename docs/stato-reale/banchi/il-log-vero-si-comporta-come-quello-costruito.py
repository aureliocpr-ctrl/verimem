# -*- coding: utf-8 -*-
"""IL CONTROLLO CHE MANCAVA: un log VERO, non costruito da me.

Alle 19:33 ho misurato che sul genere «log» il giudice da' 98.5-99.9 a una cifra
inventata in quattro celle su quattro, con `withheld_despite_judge=True` ovunque
— e ho dichiarato il limite nello stesso post: quel log l'avevo scritto io.

Qui il log e' vero e riproducibile da chiunque: l'uscita di
`git log --shortstat` su questo repo. Righe con hash, data, autore, messaggio e
il conteggio «N files changed, M insertions(+), K deletions(-)». Nessun dato
privato, nessuna riga costruita.

Il claim ha la stessa forma degli altri: una cifra che la fonte NON contiene,
attribuita a un soggetto che la fonte nomina.

  se il log vero si comporta come quello costruito (giudice sopra 80, difesa
     affidata alla sola L4.1) -> il limite e' chiuso e la riga W7-14 regge
  se si comporta come la prosa -> il mio log costruito aveva una forma che i log
     veri non hanno, e la riga va ristretta

⚠️ Un log vero contiene MOLTI numeri, e questo e' parte del genere: se il numero
inventato risultasse presente per caso, la cella non misurerebbe niente. Il
controllo lo verifica a ogni lunghezza.

CONTROLLI CHE DEVONO POTER FALLIRE: la cifra del claim assente e il soggetto
presente a ogni lunghezza; e il log dev'essere abbastanza lungo da coprire tutte
le lunghezze chieste, altrimenti il banco lo dice invece di misurare code corte.

    python docs/stato-reale/banchi/il-log-vero-si-comporta-come-quello-costruito.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

LUNGHEZZE = [1000, 2000, 4000, 6000]
CLAIM = "Il commit ha cambiato 91234 files."
CIFRA = "91234"
SOGGETTO = "files changed"


def main() -> int:
    try:
        out = subprocess.run(
            ["git", "log", "--shortstat", "--format=%h %ad %an %s", "--date=short", "-n", "400"],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: git log non eseguibile — {type(e).__name__}: {e}")
        return 1
    if out.returncode != 0:
        print(f"NON RIUSCITO: git log returncode {out.returncode}")
        return 1
    log = " ".join(r.strip() for r in out.stdout.splitlines() if r.strip())
    print(f"  log VERO da `git log --shortstat`: {len(log)} caratteri")
    if len(log) < max(LUNGHEZZE):
        print(f"  NON RIUSCITO: il log e' piu' corto di {max(LUNGHEZZE)} caratteri")
        return 1

    for n in LUNGHEZZE:
        f = log[:n]
        if CIFRA in f:
            print(f"CONTROLLO CADUTO a {n}: la cifra {CIFRA} e' nel log per caso")
            return 1
        if SOGGETTO not in f:
            print(f"CONTROLLO CADUTO a {n}: il soggetto {SOGGETTO!r} non compare")
            return 1
    print(f"  CONTROLLO retto: cifra assente e soggetto presente a tutte e {len(LUNGHEZZE)} le lunghezze")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}")
    print(f"  claim: {CLAIM!r}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "logvero.db"))

    print(f"  {'lunghezza':>10}   {'esito':<12} {'ground':>7}   lame")
    print("  " + "-" * 52)
    import json
    celle = []
    for n in LUNGHEZZE:
        ric = mem.add(CLAIM, topic=f"lv/{n}", source=log[:n], validate="full")
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        blob = json.dumps(ric.get("warnings"), default=str) + json.dumps(ric.get("moat"), default=str)
        lame = ",".join(x for x in ("L4.1", "L4-grounding", "L4-review", "L4-relazione")
                        if x in blob) or "-"
        celle.append((n, st, g, lame))
        print(f"  {n:>10}   {st:<12} {g:7.1f}   {lame}")

    gs = [g for _n, _s, g, _l in celle]
    sopra80 = sum(1 for g in gs if g > 80)
    con_giudice = sum(1 for _n, _s, _g, l in celle if "L4-grounding" in l)
    print(f"\n  ground {min(gs):.1f}-{max(gs):.1f}, ampiezza {max(gs) - min(gs):.1f}")
    print(f"  celle in cui il giudice ha dato piu' di 80 a una cifra inventata: {sopra80} su {len(celle)}")
    print(f"  celle in cui compare anche L4-grounding (difesa doppia): {con_giudice} su {len(celle)}")

    print()
    if sopra80 >= len(celle) - 1 and con_giudice <= 1:
        print("  => IL LIMITE E' CHIUSO: il log VERO si comporta come quello costruito.")
        print("     Sul genere log la difesa e' la sola regex, e la riga W7-14 regge")
        print("     su una fonte che non ho scritto io.")
    elif sopra80 == 0:
        print("  => LA RIGA VA RISTRETTA: sul log vero il giudice fa il suo lavoro.")
        print("     Il log che avevo costruito aveva una forma che i log veri non hanno.")
    else:
        print(f"  => parziale: {sopra80} celle sopra 80 su {len(celle)}. Guarda i numeri")
        print("     prima di citare la riga come chiusa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
