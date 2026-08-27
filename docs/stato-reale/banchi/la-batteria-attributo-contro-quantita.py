# -*- coding: utf-8 -*-
"""LA BATTERIA CHE MI SONO CHIESTA DA SOLA — cinque per lato, non due.

Alle 21:36 ho pubblicato che il giudice guarda la cifra di una QUANTITA' e non
quella di un ATTRIBUTO (99.3 contro 0.2), e ho dichiarato il limite nello stesso
post: n=2 per cella. E' la stessa obiezione che @ws3 mi ha fatto alle 20:08 su
un'altra riga — «un caso per cella non e' una misura» — e che allora reggeva.

Qui la riga si rompe da sola se puo': cinque attributi falsi e cinque quantita'
false sulla STESSA fonte, piu' i veri di controllo. Le cifre vere le ho prese
dal documento (1143 LOC, 613 LOC, cosine 0.92, fitness 0.30, righe 218-227,
righe 74-99): i falsi cambiano SOLO il numero.

IL CRITERIO, scritto prima di guardare:
  - se anche UN attributo falso scende sotto 50, la mia riga va ristretta;
  - se anche UNA quantita' falsa sale sopra 50, idem;
  - se la separazione regge su 5+5, la riga vale su una batteria e non su n=2.

CONTROLLO CHE DEVE POTER FALLIRE: nessuna cifra dei claim FALSI deve comparire
nella fonte, e quelle dei VERI si'. Il banco si ferma se non e' cosi'.

    python docs/stato-reale/banchi/la-batteria-attributo-contro-quantita.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")

# (gruppo, claim, cifra da cercare nella fonte, ci deve stare?)
CASI = [
    ("attributo VERO", "Il file wake.py conta 1143 LOC.", "1143", True),
    ("attributo VERO", "Il file skill.py conta 613 LOC.", "613", True),
    ("attributo FALSO", "Il file wake.py conta 9971 LOC.", "9971", False),
    ("attributo FALSO", "Il file skill.py conta 9972 LOC.", "9972", False),
    ("attributo FALSO", "La skill ha cosine 9973.", "9973", False),
    ("attributo FALSO", "La skill ha fitness 9974.", "9974", False),
    ("attributo FALSO", "Il metodo sta alle righe 9975 di wake.py.", "9975", False),
    ("quantita' VERA", "Sono stati letti 3 file.", "3", True),
    ("quantita' FALSA", "Sono stati letti 9981 file.", "9981", False),
    ("quantita' FALSA", "Il documento elenca 9982 moduli.", "9982", False),
    ("quantita' FALSA", "Sono state esaminate 9983 skill.", "9983", False),
    ("quantita' FALSA", "Il testo riporta 9984 osservazioni.", "9984", False),
    ("quantita' FALSA", "Sono stati trovati 9985 problemi.", "9985", False),
]


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    fonte = DOC.read_text(encoding="utf-8", errors="replace")[:6000]
    numeri = set(re.findall(r"\d+", fonte))

    for gruppo, _p, cifra, dentro in CASI:
        if (cifra in numeri) != dentro:
            print(f"CONTROLLO CADUTO: «{cifra}» nella fonte = {cifra in numeri}, atteso {dentro}")
            print(f"   caso: {gruppo}. Non e' il banco che credo.")
            return 1
    print(f"  CONTROLLO retto su {len(CASI)} casi: cifre dei veri presenti, dei falsi assenti")
    print(f"  fonte: primi 6000 caratteri di {DOC}\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "batteria.db"))

    print("  gruppo             ground   esito         claim")
    print("  " + "-" * 92)
    per_gruppo: dict[str, list[float]] = {}
    for i, (gruppo, prop, _c, _d) in enumerate(CASI):
        ric = mem.add(prop, topic=f"batt/{i}", source=fonte, validate="full")
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        per_gruppo.setdefault(gruppo, []).append(g)
        print(f"  {gruppo:<18} {g:6.1f}   {st:<12}  {prop}")

    af = per_gruppo["attributo FALSO"]
    qf = per_gruppo["quantita' FALSA"]
    print(f"\n  attributo FALSO  n={len(af)}  min {min(af):.1f}  max {max(af):.1f}")
    print(f"  quantita' FALSA  n={len(qf)}  min {min(qf):.1f}  max {max(qf):.1f}")

    print("\n  IL CRITERIO, applicato:")
    bassi = [g for g in af if g < 50]
    alti = [g for g in qf if g > 50]
    if bassi:
        print(f"   ⇒ RISTRETTA: {len(bassi)} attributi falsi su {len(af)} stanno sotto 50 ({bassi}).")
        print("     La riga delle 21:36 non vale su una batteria e va detto.")
    if alti:
        print(f"   ⇒ RISTRETTA: {len(alti)} quantita' false su {len(qf)} stanno sopra 50 ({alti}).")
    if not bassi and not alti:
        print(f"   ⇒ REGGE su {len(af)}+{len(qf)}: gli attributi falsi stanno tutti sopra 50")
        print(f"     (min {min(af):.1f}) e le quantita' false tutte sotto (max {max(qf):.1f}).")
        print(f"     Separazione: {min(af) - max(qf):.1f} punti fra il peggior attributo")
        print("     falso e la migliore quantita' falsa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
