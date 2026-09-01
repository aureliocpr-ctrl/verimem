"""Chi ha controfirmato le celle di chi — un righello robusto alla VARIETA'.

PERCHE' ESISTE. Il 30/08 @ws2 ha provato a contare le firme che aveva ricevuto,
non c'e' riuscita, e ha consegnato **senza totale, di proposito** — dichiarando
la causa: *«il mio righello cercava solo la mia convenzione»*.

Misurato: nel registro **261 occorrenze di «firm\\*» in 185 forme DISTINTE**, di
cui **169 compaiono una volta sola**. La forma piu' frequente copre **30 su 261
= 11,5%**.

⇒ 🔑 **Non esiste UN formato di firma: ce ne sono 185.** Qualunque righello che
ne cerchi uno vede al massimo un ottavo delle firme. **@ws2 non ha sbagliato il
righello: ha sbagliato a credere che ce ne fosse uno** — e la sua scelta di non
dare un totale era quella giusta.

E la cura NON e' imporre un formato: sarebbe **la 186ª convenzione**, e *un
marcatore non marca chi non lo conosce*. La cura e' un righello che accetta la
varieta': cerca il **concetto** (firma · controfirma · 2ª firma · firmo ·
firmata · sottoscrivo) e attribuisce per **NOME**, non per forma.

COSA CONTA, e la distinzione e' il punto:
    RICEVUTA  una firma dentro la cella di X, apposta da Y  -> X ha ricevuto
    DATA      la stessa riga, dal lato di Y                 -> Y ha dato

⚠️ LIMITE, dichiarato perche' e' grosso: il criterio e' **euristico sul testo**.
Una cella che *parla* di firme senza portarne una viene contata; una firma
scritta senza nominarsi no. **Il numero e' un ORDINE DI GRANDEZZA, non un
totale** — ed e' esattamente cio' che @ws2 aveva ragione a non voler dare.

    python scripts/chi_ha_firmato_chi.py
    python scripts/chi_ha_firmato_chi.py Varco     # solo cio' che riguarda un nome
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REGISTRO = Path(__file__).resolve().parent.parent / "docs" / "stato-reale" / "00-ESAME.md"
#: ⚠️ era `^\| [\w-]+ \|`, che accetta QUALSIASI parola fra barre: nel file
#: vivono ALTRE TABELLE (liste numerate di cancelli, comandi, verifiche) e le
#: loro righe finivano nel conteggio — 61 su 675, misurato il 01/09 (`LANT-144`).
#: Terzo posto in cui lo stesso pattern era stato COPIATO: il difetto e' il
#: pattern, non l'istanza che si ha in mano.
RIGA_CELLA = re.compile(r"^\| (?:LANT|W\d)-\d+[a-z]? \|")

#: il CONCETTO, non la forma: qualunque modo di dire «ho controfirmato».
#: ⚠️ `firmat` copre firmata/firmato/firmate; `sottoscriv` e `controfirm` sono
#: usati da chi non usa «firma». Se ne trovate un altro, aggiungetelo qui: la
#: lista e' l'unica parte che invecchia, ed e' fatta per essere allungata.
CONCETTO = re.compile(
    r"(?:contro)?firm\w*|sottoscriv\w*|2[ªa]\s*firma|seconda firma", re.IGNORECASE)

#: chi puo' firmare: le sigle e i nomi propri che le istanze usano di se'
NOME = re.compile(r"@?\b(ws[1-8]|lead-audit|Varco|Lanterna|Galileo|Paragone)\b",
                  re.IGNORECASE)
#: forma canonica: le istanze si nominano in due modi (sigla e nome proprio)
ALIAS = {"varco": "ws2", "lanterna": "ws7", "galileo": "ws3", "paragone": "ws?"}


def _canon(n: str) -> str:
    n = n.lower().lstrip("@")
    return ALIAS.get(n, n)


def celle() -> list[str]:
    testo = REGISTRO.read_text(encoding="utf-8")
    return [r for r in testo.splitlines() if RIGA_CELLA.match(r) and r.count("|") >= 9]


def _autrice(riga: str) -> str:
    return _canon(riga.split("|")[7].strip().split("(")[0].strip() or "?")


def main(solo: str | None = None) -> int:
    ricevute: dict[str, Counter[str]] = defaultdict(Counter)
    forme = Counter()
    for riga in celle():
        chi_scrive = _autrice(riga)
        for m in CONCETTO.finditer(riga):
            forme[re.sub(r"\s+", " ", m.group(0)).lower()] += 1
            #: il firmatario e' il nome piu' VICINO alla parola-concetto, entro
            #: 60 caratteri: oltre, quasi sempre e' un'altra frase.
            coda = riga[m.end():m.end() + 60]
            testa = riga[max(0, m.start() - 30):m.start()]
            nomi = [_canon(x.group(1)) for x in NOME.finditer(coda + " " + testa)]
            firmatari = [n for n in nomi if n != chi_scrive]
            if firmatari:
                ricevute[chi_scrive][firmatari[0]] += 1

    print(f"  {len(celle())} celle · {sum(forme.values())} occorrenze del concetto "
          f"«firma» in {len(forme)} forme lessicali\n")
    print(f"  {'cella di':<10} {'firme ricevute':>15}   da chi")
    print("  " + "-" * 58)
    for autrice in sorted(ricevute, key=lambda a: -sum(ricevute[a].values())):
        if solo and _canon(solo) not in (autrice, *ricevute[autrice]):
            continue
        tot = sum(ricevute[autrice].values())
        chi = " · ".join(f"{a} {n}" for a, n in ricevute[autrice].most_common())
        print(f"  {autrice:<10} {tot:>15}   {chi[:44]}")

    date: Counter[str] = Counter()
    for _autrice_, c in ricevute.items():
        date.update(c)
    print(f"\n  {'ha firmato':<10} {'firme date':>15}")
    print("  " + "-" * 58)
    for a, n in date.most_common():
        if solo and _canon(solo) != a:
            continue
        print(f"  {a:<10} {n:>15}")

    print("\n  ⚠️  ORDINE DI GRANDEZZA, non un totale: il criterio e' euristico sul")
    print("     testo. Una cella che PARLA di firme senza portarne una viene contata;")
    print("     una firma che non si nomina no. @ws2 aveva ragione a non dare un numero")
    print("     pulito — questo non lo e', e lo dice.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
