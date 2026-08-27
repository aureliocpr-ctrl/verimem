# -*- coding: utf-8 -*-
"""LA CLASSE CHE IL PRODOTTO NOMINA, CALIBRATA SU UNO.

Alle 21:44 ho misurato che su dieci falsita' con una cifra ASSENTE dalla fonte,
nove prendono 82.3-100.0 e a fermarle e' solo `L4.1`. Ne discende la domanda che
conta: cosa succede quando L4.1 non ha nulla da segnalare?

`L4.1` chiama `valori_non_nella_fonte(proposition, source)`: cerca i valori del
claim NELLA fonte. ⇒ se la cifra c'e' ma e' riferita a UN'ALTRA entita', la
regex tace per costruzione. E' lo SCAMBIO DI ATTRIBUZIONE — il caso d'uso vero:
un contratto che dice «penale 2% per il ritardo e 5% per il difetto», e un fatto
che dice «penale 5% per il ritardo». Tutte le cifre ci sono. L'attribuzione no.

IL PRODOTTO CONOSCE QUESTA CLASSE e ci ha costruito sopra la banda
(`grounding_gate.py:556-560`, verbatim):

    «Measured raw scores: true entailments cluster >=94, clear confabs <1, and
     the one mid-range Spanish entity-substitution escape sits at ~68. So
     (LOCAL_CE_MOAT_THRESHOLD .. CE_BAND_TAU_HI) isolates the CE's UNCERTAIN
     middle - where that escape lives - from the clean >=94 zone.»

⇒ E' una PROMESSA falsificabile: lo scambio di entita' vive nella banda [40,80)
e viene trattenuto. La calibrazione dichiarata e' «the ONE ... escape»: uno.

IL CRITERIO, scritto prima di guardare:
  - se uno scambio prende >= 80 e L4.1 tace, quel fatto ENTRA: la banda non lo
    isola, e la promessa vale meno di quanto la frase suggerisce;
  - se tutti stanno in [40, 80), la promessa regge su una batteria e va detto
    con la stessa forza con cui direi il contrario.

CONTROLLO CHE DEVE POTER FALLIRE: la cifra di OGNI scambio deve stare nella
fonte — altrimenti sto misurando L4.1 un'altra volta, non lo scambio.

    python docs/stato-reale/banchi/lo-scambio-di-attribuzione-elude-la-regex.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")

# La fonte dice: wake.py (1143 LOC) · skill.py (613 LOC) · cosine 0.92 ·
# fitness 0.30 · fitness 0.85 · wake.py:218-227 · skill.py:74-99
# Ogni claim prende una cifra VERA e la attribuisce alla cosa SBAGLIATA.
SCAMBI = [
    ("Il file skill.py conta 1143 LOC.", "1143", "1143 e' di wake.py"),
    ("Il file wake.py conta 613 LOC.", "613", "613 e' di skill.py"),
    ("La skill ha cosine 0.30.", "0.30", "0.30 e' la fitness"),
    ("La skill ha fitness 0.92.", "0.92", "0.92 e' la cosine"),
    ("Il metodo di wake.py sta alle righe 74-99.", "74-99", "74-99 sono di skill.py"),
]
VERI = [
    ("Il file wake.py conta 1143 LOC.", "1143"),
    ("Il file skill.py conta 613 LOC.", "613"),
]


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    fonte = DOC.read_text(encoding="utf-8", errors="replace")[:6000]

    for prop, cifra, _n in SCAMBI:
        if cifra not in fonte:
            print(f"CONTROLLO CADUTO: «{cifra}» non e' nella fonte, quindi «{prop}»")
            print("   misurerebbe L4.1 e non lo scambio.")
            return 1
    print(f"  CONTROLLO retto: le cifre di tutti e {len(SCAMBI)} gli scambi sono nella fonte")
    print(f"  fonte: primi 6000 caratteri di {DOC}\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "scambi.db"))

    def giro(prop: str, eti: str) -> tuple[str, float, str]:
        ric = mem.add(prop, topic="scambi", source=fonte, validate="full")
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        import json
        j = json.dumps(ric.get("moat"), default=str) + json.dumps(ric.get("warnings"), default=str)
        lame = ",".join(n for n in ("L4.1", "L4-grounding", "L4-relazione", "L4-review", "L1")
                        if f'"{n}"' in j or f"'{n}'" in j) or "-"
        print(f"  {eti:<44} {st:<12} {g:6.1f}   {lame}")
        return st, g, lame

    print("  claim                                        esito         ground   lame")
    print("  " + "-" * 88)
    for prop, _c in VERI:
        giro(prop, f"VERO   {prop}")
    print()
    esiti = []
    for prop, _c, nota in SCAMBI:
        st, g, lame = giro(prop, f"SCAMBIO {prop}")
        esiti.append((prop, st, g, lame, nota))

    print("\n  la promessa: lo scambio di entita' vive nella banda [40, 80) e viene trattenuto")
    ammessi = [(p, g) for p, st, g, _l, _n in esiti if st != "quarantined"]
    fuori = [(p, g) for p, _st, g, _l, _n in esiti if g >= 80]
    dentro = [g for _p, _st, g, _l, _n in esiti if 40 <= g < 80]
    print(f"   nella banda [40,80): {len(dentro)} su {len(esiti)}   valori {[f'{g:.1f}' for g in dentro]}")
    print(f"   con ground >= 80   : {len(fuori)} su {len(esiti)}")
    if ammessi:
        print(f"\n   ⇒ {len(ammessi)} scambi su {len(esiti)} sono AMMESSI:")
        for p, g in ammessi:
            print(f"        {g:6.1f}  {p}")
        print("     La banda non li isola. La promessa di grounding_gate.py:556 e'")
        print("     calibrata su un caso e su una batteria non regge.")
    elif fuori:
        print(f"\n   ⇒ nessuno ammesso, ma {len(fuori)} stanno FUORI dalla banda:")
        print("     sono trattenuti da qualcos'altro, non dal presidio che li nomina.")
        for p, g in fuori:
            print(f"        {g:6.1f}  {p}")
    else:
        print("\n   ⇒ REGGE: tutti gli scambi cadono nella banda e vengono trattenuti,")
        print("     e la calibrazione su un caso ha retto su cinque.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
