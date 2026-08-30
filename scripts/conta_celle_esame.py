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
SIMBOLO = re.compile(r"[🔴🟢🟡⛔🚫📋]")   # 📋 = cella di metodo (30/08)
#: i simboli che NON sono verdetti ma vengono usati come tali: servono a dire
#: all'autrice cosa ha scritto, non a indovinare cosa intendeva. Il 28/08 cinque
#: celle usavano ✅ o ⚠️ — la terza volta in un giorno che qualcuno prende il
#: simbolo piu' naturale invece di uno dei cinque, e ogni volta il difetto era
#: della legenda, non di chi la usava.
ALTRI_SIMBOLI = re.compile(r"[✅⚠️❌⚪🆕🔧🚨]")   # 📋 e' uscito da qui: ora e' in legenda


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
        + (f" · 📋 di metodo {conto['📋']}" if conto["📋"] else "")
        + f"   (su {len(celle)} celle)"
    )
    if conto["?"]:
        print(f"⚠️  {conto['?']} celle senza simbolo di LEGENDA nella colonna verdetto:")
        for riga in celle:
            if verdetto(riga) == "?":
                ident = RIGA_CELLA.match(riga).group(0).strip("| ")
                altri = "".join(dict.fromkeys(ALTRI_SIMBOLI.findall(riga.split("|")[6])))
                autrice = riga.split("|")[7].strip()[:12]
                print(f"     {ident:9} (di {autrice or '?'}) usa «{altri or '—'}»"
                      f" — la legenda ha 🔴🟢🟡⛔🚫📋")
        print("   ⇒ il difetto e' della LEGENDA se il simbolo usato e' quello naturale:"
              " chiedi all'autrice quale dei cinque intendeva, non cambiarlo tu.")
    # 29/08: una cella che contiene un blocco di codice (```) o un a-capo SPEZZA
    # la riga della tabella markdown: le righe di continuazione non fanno piu'
    # parte della tabella e la colonna non si allinea. Trovato addosso a me:
    # 19 celle su 20 rotte erano mie, e i due righelli che avevo usato per
    # cercarle si contraddicevano, perche' il primo filtrava su `count("|") >= 9`
    # e cosi' SALTAVA proprio le celle spezzate. Il controllo giusto e' banale:
    # una riga di tabella comincia con `|` e DEVE finire con `|`.
    testo = REGISTRO.read_text(encoding="utf-8")
    # 🔴 30/08: questo blocco chiamava tutto «SPEZZATE» e concludeva «difetto di
    # FORMA, nessun numero cambia». ERA FALSO, e la diagnosi sbagliata e' rimasta
    # per giorni davanti a chiunque eseguisse lo script. Sono DUE difetti:
    #   A  la cella e' su piu' righe fisiche e una continuazione la chiude
    #      -> vera resa rotta, il contenuto c'e'
    #   B  la riga e' SOLA, ha 8 pipe invece di 9 e la riga dopo e' gia' un'altra
    #      cella -> il testo e' TRONCATO, e cio' che manca e' l'ULTIMA colonna:
    #      il REGIME. Cioe' proprio il campo che rende la misura ripetibile.
    # ⇒ La differenza decide la cura: A si unisce, B NON si puo' riparare
    #   aggiungendo un `|` — lo si farebbe sembrare completo mentendo.
    righe_t = testo.splitlines()
    A, B = [], []
    for i, r in enumerate(righe_t):
        if not (RIGA_CELLA.match(r) and not r.rstrip().endswith("|")):
            continue
        ident = RIGA_CELLA.match(r).group(0).strip("| ")
        dopo = righe_t[i + 1] if i + 1 < len(righe_t) else ""
        (B if (RIGA_CELLA.match(dopo) or not dopo.strip()) else A).append(ident)
    if A:
        print(f"⚠️  {len(A)} celle su PIU' RIGHE (resa rotta, contenuto integro):")
        print(f"     {' '.join(A[:14])}{' …' if len(A) > 14 else ''}")
        print("   ⇒ un blocco ``` dentro una cella va reso su una riga sola.")
    if B:
        print(f"🔴 {len(B)} celle TRONCATE (manca l'ultima colonna, il REGIME):")
        print(f"     {' '.join(B[:14])}{' …' if len(B) > 14 else ''}")
        print("   ⇒ NON e' un difetto di forma: il testo e' stato tagliato in scrittura")
        print("     e con esso il regime. Chiudere la riga con un `|` la fa sembrare")
        print("     completa e MENTE. O si recupera il regime, o si dichiara che manca.")
    print(f"id duplicati: {', '.join(doppi) if doppi else 'nessuno'}")
    return 1 if doppi or conto["?"] else 0


if __name__ == "__main__":
    sys.exit(main())
