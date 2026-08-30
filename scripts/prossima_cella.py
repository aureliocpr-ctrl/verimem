"""Il prossimo numero di cella LIBERO per una sigla del registro.

PERCHE' ESISTE. Il 30/08 alle 19:04 ho scoperto **sei id duplicati in una volta
sola**: `LANT-68` … `LANT-73` esistevano gia', e ne avevo appena scritte altre
sei con gli stessi numeri. Il massimo nel file era **89**.

La causa non e' distrazione: **ho scritto il numero a mano partendo dall'ultimo
che RICORDAVO**, invece che da quello che il file DICE. Con otto istanze che
scrivono e un `rebase` fra un inserimento e l'altro, «l'ultimo che ricordo» e'
gia' vecchio quando lo scrivo. ⇒ E' la stessa classe che avevo denunciato io in
`LANT-61` — **un numero di STATO scritto a mano** — e in `LANT-64` sulle ore
battute a tastiera: **cinque derive su cinque erano numeri digitati, zero quelle
lette da un comando**.

⇒ La cura non e' «stare piu' attenti»: e' **non digitare piu' quel numero**.

    python scripts/prossima_cella.py LANT        -> 96
    python scripts/prossima_cella.py W2          -> il prossimo per ws2
    python scripts/prossima_cella.py LANT --riga -> la riga gia' pronta da incollare

E dentro uno script che inserisce celle:

    from scripts.prossima_cella import prossimo
    ident = f"LANT-{prossimo('LANT')}"

⚠️ Va chiamato **dopo** il `git rebase`, non prima: e' il rebase che porta le
celle altrui, e un numero preso prima e' gia' scaduto.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REGISTRO = Path(__file__).resolve().parents[1] / "docs" / "stato-reale" / "00-ESAME.md"


def usati(sigla: str, registro: Path = REGISTRO) -> list[int]:
    """Tutti i numeri gia' presenti per quella sigla, in ordine."""
    #: la riga di cella comincia con `| SIGLA-n |`; il suffisso di lettera
    #: (`W7-20b`) e' legittimo e va contato come occupato.
    schema = re.compile(rf"^\|\s*{re.escape(sigla)}-(\d+)[a-z]?\s*\|")
    testo = registro.read_text(encoding="utf-8")
    return sorted({int(m.group(1)) for m in (schema.match(r) for r in testo.splitlines()) if m})


def prossimo(sigla: str, registro: Path = REGISTRO) -> int:
    n = usati(sigla, registro)
    return (n[-1] + 1) if n else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sigla", help="LANT, W2, W7, …")
    ap.add_argument("--riga", action="store_true", help="stampa la riga vuota da incollare")
    ap.add_argument("--buchi", action="store_true", help="elenca i numeri MAI usati sotto il massimo")
    a = ap.parse_args()

    n = usati(a.sigla)
    if not n:
        print(f"  nessuna cella {a.sigla}-* nel registro: il prossimo e' {a.sigla}-1")
        return 0

    p = prossimo(a.sigla)
    if a.riga:
        print(f"| {a.sigla}-{p} | DOMANDA | classe | lingua | PORTA | VERDETTO | "
              f"{a.sigla.lower()} | REGIME: comando + commit + store |")
        return 0

    print(f"  {a.sigla}: {len(n)} celle, da {n[0]} a {n[-1]}  ->  il prossimo e' {a.sigla}-{p}")
    if a.buchi:
        #: un buco non e' un errore — una cella puo' essere stata ritirata — ma
        #: sapere quali sono evita di «riempirli» credendo di essere ordinati:
        #: un id riusato e' peggio di un id mancante, perche' due celle diverse
        #: finiscono sotto lo stesso nome e chi cita non sa quale intendeva.
        buchi = [i for i in range(n[0], n[-1]) if i not in set(n)]
        print(f"  buchi ({len(buchi)}): {buchi if len(buchi) <= 30 else str(buchi[:30]) + ' …'}")
        print("  ⚠️ NON riempirli: un id riusato e' peggio di un id mancante.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
