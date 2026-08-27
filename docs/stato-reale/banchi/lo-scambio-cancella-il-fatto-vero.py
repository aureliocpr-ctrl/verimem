# -*- coding: utf-8 -*-
"""IL FATTO AMMESSO NON E' ANCORA IL DANNO: il danno e' cosa la memoria RISPONDE.

Il banco `lo-scambio-di-attribuzione-elude-la-regex.py` ha misurato che cinque
scambi di attribuzione su cinque entrano con grounding 99.7-100.0 e `layers=[]`.
Nei suoi log, in due esecuzioni su due, comparivano righe come:

  flow.supersession branch='same-source evolution' loser_id=... winner_id=...

⇒ non e' solo che il falso entra: sembra che PRENDA IL POSTO del vero. Questo
banco lo verifica dalla porta che un agente usa davvero — scrive il fatto VERO,
poi lo scambio, e poi CHIEDE.

CONTROLLO CHE DEVE POTER FALLIRE: il fatto vero deve essere ammesso e
recuperabile PRIMA che arrivi lo scambio. Se non lo e', non sto misurando una
sostituzione: sto misurando una scrittura che non c'e' mai stata.

⚠️ NOTA DI METODO, dichiarata: i due fatti stanno nello stesso topic, che e' cio'
che permette la supersessione. E' un uso realistico — un utente scrive piu'
fatti sullo stesso argomento — ma con topic separati la supersessione non
scatterebbe e il vero resterebbe accanto al falso. Il banco misura entrambi.

    python docs/stato-reale/banchi/lo-scambio-cancella-il-fatto-vero.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")
VERO = "Il file skill.py conta 613 LOC."
SCAMBIO = "Il file skill.py conta 1143 LOC."
DOMANDA = "quanti LOC ha skill.py"


def _mostra(mem, etichetta: str) -> list[str]:
    try:
        res = mem.search(DOMANDA, k=4)
    except Exception as e:  # noqa: BLE001
        print(f"   {etichetta}: ricerca fallita — {type(e).__name__}: {e}")
        return []
    print(f"   {etichetta}:")
    fuori = []
    for x in res:
        t = str(x.get("proposition") or x.get("text") or "")[:60]
        st = str(x.get("status", "?"))
        fuori.append(t)
        print(f"      {st:<12} {t}")
    if not res:
        print("      (nessun risultato)")
    return fuori


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    fonte = DOC.read_text(encoding="utf-8", errors="replace")[:6000]

    from verimem.client import Memory  # noqa: PLC0415

    for stesso_topic in (True, False):
        eti = "STESSO topic" if stesso_topic else "topic SEPARATI"
        print(f"\n══ {eti} " + "═" * 50)
        mem = Memory(str(Path(tempfile.mkdtemp()) / "sost.db"))

        t1 = "misure/skill" if stesso_topic else "misure/skill/vero"
        t2 = "misure/skill" if stesso_topic else "misure/skill/scambio"

        r1 = mem.add(VERO, topic=t1, source=fonte, validate="full")
        print(f"   scritto il VERO    : {r1.get('status')}  ground {float(r1.get('grounding_score') or -1):.1f}")
        if str(r1.get("status")) == "quarantined":
            print("   CONTROLLO CADUTO: il vero non e' entrato, non c'e' niente da sostituire")
            return 1
        prima = _mostra(mem, "la memoria risponde PRIMA")

        r2 = mem.add(SCAMBIO, topic=t2, source=fonte, validate="full")
        print(f"   scritto lo SCAMBIO : {r2.get('status')}  ground {float(r2.get('grounding_score') or -1):.1f}")
        dopo = _mostra(mem, "la memoria risponde DOPO")

        vero_prima = any("613" in t for t in prima)
        vero_dopo = any("613" in t for t in dopo)
        falso_dopo = any("1143" in t for t in dopo)
        print(f"   ⇒ il vero (613) c'era prima: {vero_prima} · c'e' dopo: {vero_dopo}"
              f" · il falso (1143) c'e' dopo: {falso_dopo}")
        if vero_prima and not vero_dopo and falso_dopo:
            print("   ⇒ SOSTITUITO: chi chiede riceve la cifra sbagliata, e quella giusta")
            print("     non e' piu' fra le risposte.")
        elif vero_dopo and falso_dopo:
            print("   ⇒ CONVIVONO: chi chiede riceve entrambe e non ha modo di scegliere.")
        else:
            print("   ⇒ altro caso: guarda le righe sopra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
