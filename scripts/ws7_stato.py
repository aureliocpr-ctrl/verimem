"""Lo stato corrente di ws7, LETTO dal registro invece che ricordato.

    python scripts/ws7_stato.py            # stato compatto
    python scripts/ws7_stato.py --ultime 8 # piu' celle recenti

PERCHE' ESISTE. Il 30/08 ho riscritto **tre volte** il prompt del mio loop
(`0ac44255`, `36e999d3`, `c7dbaee0`) e **tutte e tre le volte si e'
ridisallineato entro l'ora**: elencava C10 «in corso» quando era chiuso, un A/B
«in esecuzione» gia' concluso, e «11 celle senza PORTA» due minuti dopo che
avevo misurato che erano zero.

⇒ 🔑 **Un prompt che CONTIENE lo stato e' un numero di STATO scritto a mano** —
la mia stessa `LANT-61`, applicata allo strumento con cui lavoro invece che al
README. **La cura e' la stessa: si sostituisce col comando che lo calcola.**

⇒ Il prompt del loop deve portare **perimetro e regole** (stabili) e **puntare**
allo stato, non elencarlo. Questo script e' il puntatore.

Costa meno di un secondo: legge un file e conta.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
REGISTRO = RADICE / "docs" / "stato-reale" / "00-ESAME.md"
CELLA = re.compile(r"^\| (LANT-\d+[a-z]?) \|")
#: i verdetti che segnalano un lavoro NON concluso
APERTI = ("🟡", "⛔")


def _riga(r: str) -> tuple[str, str, str]:
    col = [c.strip() for c in r.split("|")]
    ident = col[1]
    domanda = re.sub(r"\*\*|`", "", col[2])[:88]
    verdetto = re.sub(r"\*\*|`", "", col[6] if len(col) > 6 else "")[:96]
    return ident, domanda, verdetto


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ultime", type=int, default=5)
    a = ap.parse_args()

    testo = REGISTRO.read_text(encoding="utf-8")
    mie = [r for r in testo.splitlines() if CELLA.match(r) and r.count("|") >= 9]
    if not mie:
        print("  nessuna cella LANT-* nel registro")
        return 1

    numeri = [int(CELLA.match(r).group(1).split("-")[1]) for r in mie]
    sha = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=RADICE,
                         capture_output=True, text=True).stdout.strip()
    print(f"  ws7 — {len(mie)} celle LANT (da {min(numeri)} a {max(numeri)}) · "
          f"prossimo id LANT-{max(numeri) + 1} · commit {sha}")

    print(f"\n  ultime {a.ultime} celle:")
    for r in mie[-a.ultime:]:
        ident, domanda, verdetto = _riga(r)
        print(f"     {ident:9}  {domanda}")
        print(f"     {'':9}  → {verdetto}")

    #: gli APERTI non stanno in una lista a parte che invecchia: sono le celle
    #: con un verdetto 🟡 o ⛔ nel registro. Se una si chiude, sparisce da qui
    #: SENZA che nessuno debba ricordarsi di cancellarla.
    #: ⚠️ LIMITE DEL CRITERIO, dichiarato: 🟡 non significa «aperta» — significa
    #: «non completamente verde». Molte 🟡 sono CHIUSE con un limite dichiarato
    #: (es. una misura valida che non si generalizza). ⇒ **Questa lista e' una
    #: lista di COSE DA GUARDARE, non di lavori da finire**: separarle richiede
    #: di leggerle, e un criterio sintattico su un fenomeno semantico sbaglia in
    #: entrambe le direzioni (`LANT-104`).
    aperti = [r for r in mie if any(s in r.split("|")[6] for s in APERTI)]
    print(f"\n  celle MIE non-verdi (🟡/⛔) — da GUARDARE, non necessariamente da finire: {len(aperti)}")
    for r in aperti[-6:]:
        ident, domanda, _ = _riga(r)
        print(f"     {ident:9}  {domanda}")
    if len(aperti) > 6:
        print(f"     … e altre {len(aperti) - 6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
