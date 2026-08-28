"""QUANTO VALE `L4.2` SULLA CODA VERA — prima di chiedere il claim per curarlo.

W7-30 ha isolato che `L4.2` legge la grandezza **a destra** del numero, e su una
tabella allineata a destra c'e' `in` o `file`, mai l'etichetta. W7-31 ha misurato
che su source tabellari da' **8 falsi allarmi su 8** mentre `L4.1` ne da' zero.
@ws6 e @ws2 hanno confermato il difetto per conto loro (una terza istanza ha
visto prendere `ba` da dentro uno SHA come nome di grandezza).

Manca il numero che dice se vale la pena curarlo: **quanti dei quarantinati vivi
porta sulla coscienza `L4.2`?** E' la stessa domanda di W7-33 su `L1.13`, e si
risponde allo stesso modo.

⚠️ MA C'E' UNA DIFFERENZA CHE CAMBIA IL METODO: `L4.1` e `L4.2` hanno bisogno
della **fonte**, e la fonte NON e' persistita (`facts` ha 31 colonne e nessuna
la contiene). ⇒ Non posso rieseguire il layer sui quarantinati come ho fatto col
detector di `L1.13`, che guarda la sola proposizione.
⇒ Uso cio' che il prodotto HA conservato: la colonna `quarantined_by`, che dal
07/08 registra chi ha deciso.

Tre numeri, e il terzo e' quello che decide:
  ① quanti quarantinati vivi portano `quarantined_by = 'L4.2'`
  ② quanti ne portano uno qualsiasi (la copertura della colonna)
  ③ quanti, fra quelli, hanno una proposizione che SOMIGLIA a un referto
     (numero seguito da una parola funzionale: la forma che innesca il difetto)

CONTROLLI CHE POSSONO FALLIRE:
 (1) se `quarantined_by` non porta MAI 'L4.2', il numero e' zero per costruzione
     e va letto come «non registrato», non come «non succede».
 (2) il ③ e' un INDIZIO sulla forma, non una diagnosi: non posso rieseguire il
     layer senza la fonte, e lo dico invece di far finta.

    python -u docs/stato-reale/banchi/la-taglia-di-L4-2-sulla-coda-vera.py
"""

from __future__ import annotations

import collections
import re
import sqlite3
import sys

# La forma che innesca il difetto: un numero seguito da una parola FUNZIONALE
# invece che dall'etichetta della grandezza. E' quello che succede in una
# tabella allineata, dove l'etichetta sta a sinistra.
_NUM_POI_FUNZIONALE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s+(?:in|su|di|e|a|da|per|con|of|on|to|for|and|the)\b",
    re.IGNORECASE)


def main() -> int:
    try:
        from verimem.config import CONFIG
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = list(con.execute(
        "SELECT proposition, quarantined_by FROM facts "
        "WHERE status='quarantined' AND superseded_by IS NULL"))
    n = len(righe)
    print(f"  db: {CONFIG.semantic_db}")
    print(f"  quarantinati vivi: {n}")
    if not n:
        print("  NON RIUSCITO: nessuna riga.")
        return 1

    dist = collections.Counter((qb or "<VUOTA>").strip() or "<VUOTA>"
                               for _p, qb in righe)
    print("\n  == ① e ② CHI HA DECISO, sui quarantinati vivi")
    for k, v in dist.most_common(10):
        print(f"     {v:>5}  ({100.0 * v / n:>5.1f}%)  {k}")

    l42 = dist.get("L4.2", 0)
    l41 = dist.get("L4.1", 0)
    vuote = dist.get("<VUOTA>", 0)
    print(f"\n     L4.2 : {l42}      L4.1 : {l41}      colonna vuota : {vuote}")

    print("\n  -- CONTROLLO (1): la colonna registra mai L4.2?")
    if l42 == 0:
        print("     ZERO - e non vuol dire «non succede»: vuol dire NON")
        print("     REGISTRATO. La colonna esiste dal 07/08 e il difetto e'")
        print("     stato trovato il 28/08, quindi la coda potrebbe portarlo")
        print("     sotto un'altra etichetta (moat, gate) o non portarlo.")
    else:
        print(f"     {l42} righe registrano L4.2 come decisore")

    print("\n  == ③ LA FORMA CHE INNESCA IL DIFETTO, sull'intera coda")
    forma = [p for p, _qb in righe if p and _NUM_POI_FUNZIONALE.search(p)]
    print(f"     proposizioni con «numero + parola funzionale»: {len(forma)}"
          f" su {n}   ({100.0 * len(forma) / n:.1f}%)")
    for p in forma[:5]:
        m = _NUM_POI_FUNZIONALE.search(p)
        print(f"       [{m.group(0).strip()}]  {p[:64]}")

    print("\n  -- CONTROLLO (2): cosa questo NON dice")
    print("     Non ho rieseguito `L4.2`: gli serve la FONTE, e la fonte non e'")
    print("     persistita. Il ③ misura la FORMA della proposizione, non il")
    print("     verdetto del layer. ⇒ E' un indizio sulla superficie esposta,")
    print("     non una conta di falsi allarmi.")
    print("     Il numero vero si potra' avere solo sulle scritture FUTURE,")
    print("     come per la cura di L1.13 (W7-33).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
