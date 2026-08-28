"""Conta i verdetti di `docs/stato-reale/00-ESAME.md`.

Esiste perche' il conto a occhio ha sbagliato: una cella che dice
«🟢 sì, dopo cura (era 🔴)» contiene entrambi i simboli, e un `grep` che
cerca «contiene 🔴» la conta rossa. Il 28/08 tre celle su 69 erano
classificate cosi', e il conto pubblicato nel registro era sbagliato.

Il verdetto di una cella e' il PRIMO simbolo della sua colonna verdetto,
non un simbolo qualsiasi nel testo.

Quando la legenda del registro guadagna uno stato, va aggiunto QUI: il 28/08
e' stato introdotto `RITIRATA` e per qualche minuto lo script ha continuato a
segnalare quelle celle come «senza verdetto» — lo strumento che verifica una
convenzione invecchia insieme a lei.

    python scripts/conta_celle_esame.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

REGISTRO = Path(__file__).resolve().parent.parent / "docs" / "stato-reale" / "00-ESAME.md"

#: una riga-cella: `| <id> | <domanda> | ... |` con almeno le nove colonne.
RIGA_CELLA = re.compile(r"^\| [\w-]+ \|")
#: il verdetto e' il PRIMO simbolo, non uno qualsiasi: vedi il docstring.
SIMBOLO = re.compile(r"[🔴🟢🟡⛔🚫]")


def verdetto(riga: str) -> str:
    trovato = SIMBOLO.search(riga.split("|")[6])
    return trovato.group(0) if trovato else "?"


def main() -> int:
    testo = REGISTRO.read_text(encoding="utf-8")
    celle = [
        r for r in testo.splitlines() if RIGA_CELLA.match(r) and r.count("|") >= 9
    ]
    conto = Counter(verdetto(r) for r in celle)

    ids = [RIGA_CELLA.match(r).group(0).strip("| ") for r in celle]
    doppi = sorted(k for k, v in Counter(ids).items() if v > 1)

    print(
        f"🔴 rossi {conto['🔴']} · 🟢 verdi {conto['🟢']} · "
        f"🟡 parziali {conto['🟡']}"
        + (f" · ⛔ non misurabili {conto['⛔']}" if conto["⛔"] else "")
        + (f" · 🚫 ritirate {conto['🚫']}" if conto["🚫"] else "")
        + f"   (su {len(celle)} celle)"
    )
    if conto["?"]:
        print(f"⚠️  {conto['?']} celle senza simbolo nella colonna verdetto")
    print(f"id duplicati: {', '.join(doppi) if doppi else 'nessuno'}")
    return 1 if doppi or conto["?"] else 0


if __name__ == "__main__":
    sys.exit(main())
