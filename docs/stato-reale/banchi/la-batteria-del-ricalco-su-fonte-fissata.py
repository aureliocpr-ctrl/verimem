# -*- coding: utf-8 -*-
"""LA BATTERIA DEL RICALCO, su una fonte che NON si muove.

Alle 19:57 ho misurato che lo stesso fatto vero passa a 88.4 se il claim cita il
titolo del commit per esteso e crolla a 0.2-2.7 se lo si accorcia o lo si toglie.
Era n=1: UN fatto, cinque forme. Stasera una regolarita' su poche celle mi e'
caduta tre volte appena l'ho messa su una batteria.

E alle 19:59 ho dovuto ritirare una misura per irriproducibilita': usavo
`git log` di questo repo come fonte, e noi ci committiamo — sei commit nuovi in
tre minuti. La cura che avevo scritto era «fissare la fonte a uno SHA o a un
file salvato». Qui e' applicata: la fonte e'
`docs/stato-reale/banchi/fonte-log-fissata.txt`, committato accanto al banco.
Chiunque lo rilegga fra un mese misura lo stesso testo.

La batteria: sei fatti VERI diversi, ognuno in due forme.

  CITA        «Il commit <titolo per esteso> ha aggiunto N inserzioni.»
  RIFORMULA   «Un commit di documentazione ha aggiunto N inserzioni.»

Stessa verita', due forme, sei volte.

  se CITA passa e RIFORMULA no, su piu' di quattro fatti su sei
     -> il pattern regge su una batteria e non era n=1
  se gli esiti si mescolano
     -> era n=1, e la riga delle 19:57 va ristretta

CONTROLLI CHE DEVONO POTER FALLIRE: ogni conteggio dev'essere univoco nel testo
(altrimenti non si sa a quale commit il giudice lo attribuisca) e il titolo
dev'essere presente.

    python docs/stato-reale/banchi/la-batteria-del-ricalco-su-fonte-fissata.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

FONTE_FILE = Path("docs/stato-reale/banchi/fonte-log-fissata.txt")
QUANTI = 6


def main() -> int:
    if not FONTE_FILE.exists():
        print(f"NON RIUSCITO: {FONTE_FILE} non c'e' — la fonte fissata manca")
        return 1
    grezzo = FONTE_FILE.read_text(encoding="utf-8", errors="replace")
    righe = grezzo.splitlines()
    log = " ".join(x.strip() for x in righe if x.strip()).replace("@@", "")
    print(f"  fonte FISSATA: {FONTE_FILE} — {len(log)} caratteri, {len(righe)} righe")

    voci, corrente = [], None
    for riga in righe:
        r = riga.strip()
        if r.startswith("@@"):
            _h, _, s = r[2:].partition("|")
            corrente = s
        elif "insertion" in r and corrente:
            m = re.search(r"(\d+) insertion", r)
            if m:
                voci.append((corrente, m.group(1)))
            corrente = None

    buoni = [
        (s, c) for s, c in voci
        if len(re.findall(rf"\b{c}\b", log)) == 1 and 20 < len(s) < 70 and log.find(s[:30]) >= 0
    ]
    if len(buoni) < QUANTI:
        print(f"NON RIUSCITO: fatti con conteggio univoco trovati {len(buoni)}, ne servono {QUANTI}")
        return 1
    buoni.sort(key=lambda sc: log.find(sc[0][:30]))
    scelti = buoni[:QUANTI]
    print(f"  CONTROLLO retto: {QUANTI} fatti con conteggio univoco e titolo presente\n")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "batt.db"))

    print(f"  {'ins':>6}  {'CITA':>16}  {'RIFORMULA':>16}   titolo")
    print("  " + "-" * 76)
    esiti = []
    for sog, ins in scelti:
        riga = []
        for forma, prop in (
            ("CITA", f"Il commit «{sog}» ha aggiunto {ins} inserzioni."),
            ("RIFORMULA", f"Un commit di documentazione ha aggiunto {ins} inserzioni."),
        ):
            ric = mem.add(prop, topic=f"br/{forma}/{ins}", source=log, validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            riga.append((st != "quarantined", g))
        (ec, gc), (er, gr) = riga
        esiti.append((ins, ec, gc, er, gr, sog))
        print(f"  {ins:>6}  {('ENTRA' if ec else 'ferma') + f' {gc:6.1f}':>16}"
              f"  {('ENTRA' if er else 'ferma') + f' {gr:6.1f}':>16}   {sog[:34]}")

    cita_ok = sum(1 for _i, ec, _gc, _er, _gr, _s in esiti if ec)
    rif_ok = sum(1 for _i, _ec, _gc, er, _gr, _s in esiti if er)
    gc_tutti = [gc for _i, _ec, gc, _er, _gr, _s in esiti]
    gr_tutti = [gr for _i, _ec, _gc, _er, gr, _s in esiti]
    print(f"\n  CITA      {cita_ok} su {QUANTI} ammessi   ground {min(gc_tutti):5.1f}-{max(gc_tutti):5.1f}")
    print(f"  RIFORMULA {rif_ok} su {QUANTI} ammessi   ground {min(gr_tutti):5.1f}-{max(gr_tutti):5.1f}")

    print()
    if cita_ok >= QUANTI - 1 and rif_ok <= 1:
        print("  => IL PATTERN REGGE SU UNA BATTERIA: lo stesso fatto vero passa citando")
        print("     e viene rifiutato riformulato, su sei fatti diversi. Non era n=1.")
    elif cita_ok == rif_ok:
        print("  => NON C'E' DIFFERENZA fra le due forme su questa batteria: la riga")
        print("     delle 19:57 era n=1 e va ristretta.")
    else:
        print(f"  => parziale: CITA {cita_ok}/{QUANTI}, RIFORMULA {rif_ok}/{QUANTI}.")
        print("     Non basta a dichiarare il pattern, e va detto cosi'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
