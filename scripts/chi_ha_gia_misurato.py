"""Chi ha già misurato questo? — indice inverso del registro, per ARGOMENTO.

Esiste perché stanotte @ws2 ha scoperto di aver duplicato due celle di @ws4
(`W7-30`/`W7-31` alle 23:05, `W2-31`/`W2-42` un'ora dopo, stesso oggetto) e l'ha
scoperto **dopo aver misurato**, cercando celle da controfirmare. Sue parole:
«e' la QUINTA volta stanotte che dichiaro nuovo qualcosa di gia' registrato».

Il registro ha ~170 celle e le sigle sono per AUTRICE (`W2-n`, `LANT-n`, `W7-n`):
chi sta per misurare `L4.2` non ha modo di sapere chi l'ha gia' guardato senza
leggere tutto. **Non manca disciplina: manca un indice per argomento** — e la
regola che abbiamo pagato piu' volte dice di curare lo strumento, non le persone.

    python scripts/chi_ha_gia_misurato.py L4.2
    python scripts/chi_ha_gia_misurato.py supersession
    python scripts/chi_ha_gia_misurato.py            # indice completo dei layer

Cerca nel testo INTERO della cella (non solo nella domanda), stampa id, autrice e
la domanda troncata. Il confronto e' case-insensitive; un punto nel termine e'
trattato alla lettera, cosi' `L4.1` non pesca `L4-11`.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

REGISTRO = Path(__file__).resolve().parent.parent / "docs" / "stato-reale" / "00-ESAME.md"
RIGA_CELLA = re.compile(r"^\| [\w-]+ \|")
#: i nomi di layer che il prodotto usa: e' l'asse su cui le celle si duplicano.
LAYER = re.compile(r"\bL\d(?:\.\d+)?\b|\bL\d-[a-z]+\b|\bmoat\b|\bgate\b", re.IGNORECASE)


def celle() -> list[str]:
    testo = REGISTRO.read_text(encoding="utf-8")
    return [r for r in testo.splitlines() if RIGA_CELLA.match(r) and r.count("|") >= 9]


def _campi(riga: str) -> tuple[str, str, str]:
    parti = riga.split("|")
    ident = RIGA_CELLA.match(riga).group(0).strip("| ")
    # la colonna autrice porta spesso una parentesi («ws7 (collega)», «ws1 (riporta ws2)»):
    # per l'indice serve la SIGLA, non la nota, altrimenti la stessa persona compare due volte.
    autrice = parti[7].strip().split("(")[0].strip() or "?"
    return ident, autrice[:10], parti[2].strip()[:64]


def cerca(termine: str) -> int:
    pat = re.compile(re.escape(termine), re.IGNORECASE)
    trovate = [r for r in celle() if pat.search(r)]
    if not trovate:
        print(f"  «{termine}»: nessuna cella. Sei la prima — scrivilo nella cella.")
        return 0
    print(f"  «{termine}» compare in {len(trovate)} celle:\n")
    per_autrice = Counter()
    for riga in trovate:
        ident, autrice, domanda = _campi(riga)
        per_autrice[autrice] += 1
        print(f"    {ident:9} ({autrice:12}) {domanda}")
    if len(per_autrice) > 1:
        conto = " · ".join(f"{a} {n}" for a, n in per_autrice.most_common())
        print(f"\n  ⚠️  {len(per_autrice)} autrici diverse su questo tema: {conto}")
        print("     Prima di misurare, leggi le loro: potresti avere gia' la risposta,")
        print("     o poter firmare la loro invece di rifare la stessa cosa.")
    return 0


def indice() -> int:
    conto: Counter[str] = Counter()
    autrici: dict[str, set[str]] = {}
    for riga in celle():
        _ident, autrice, _dom = _campi(riga)
        for nome in {m.group(0).upper() for m in LAYER.finditer(riga)}:
            conto[nome] += 1
            autrici.setdefault(nome, set()).add(autrice)
    print(f"  indice per argomento — {len(celle())} celle, {len(conto)} temi\n")
    print(f"  {'tema':<16} {'celle':>5}  {'autrici':>7}   chi")
    print("  " + "-" * 62)
    for nome, n in conto.most_common():
        chi = sorted(autrici[nome])
        segno = "  ⚠️ duplicabile" if len(chi) > 2 and n > 3 else ""
        print(f"  {nome:<16} {n:>5}  {len(chi):>7}   {' '.join(chi)[:28]}{segno}")
    return 0


if __name__ == "__main__":
    sys.exit(cerca(" ".join(sys.argv[1:])) if len(sys.argv) > 1 else indice())
