"""Il rilevatore regge 8/8 sui casi costruiti e sbaglia 10 su 10 sul corpus.

Il banco gemello (`ws3-il-rilevatore-del-numero-solo-strutturale.py`) dava
**8/8 su due popolazioni**, con **due controlli in piedi**: prendeva il caso
vero, e spegnendo l'astensione i casi B si sporcavano — cioe' la regola era
*necessaria*, non decorativa. Sarebbe bastato per proporlo.

Sul corpus vero: **10 segnalati su 6002**, e **letti uno per uno sono 10 falsi
positivi su 10.**

    #  numero    marcatore agganciato   cos'era DAVVERO
    1  27119     «righe 27119»          unita' in una TABELLA
    9  279       «righe 279»            idem
    3  1         «riga 1»               separatore di un dump di log
    4  1         «riga 1»               idem (l'1 del claim era VERIMEM_AUDIT_LOG=1)
    5  2026      «schedule 2026»        nome di EVENTO CRON, e 2026 e' un anno
    6  2026      «schedule 2026»        idem
    7  1         «NO 1»                 cella di tabella («no» e' nella regex)
    8  0.40      «nota 0.40»            INTESTAZIONE DI COLONNA
    2  99.982    nessun marcatore nel contesto mostrato
    10 937       nessun marcatore nel contesto mostrato

LA CAUSA, e non e' un difetto della regex: **`_RIFERIMENTO_RE` e' nata per
SALTARE i numeri di sezione durante l'estrazione delle quantita'** (`29ab5544`).
Li' un falso aggancio e' **conservativo** — salti un numero, al peggio manchi un
controllo. Riusata come rilevatore **POSITIVO**, lo stesso falso aggancio
diventa **un'accusa**.

🔑 **Riusare un componente ne INVERTE il profilo di rischio quando si inverte il
verso del verdetto.** Un filtro che sbaglia tace; un accusatore che sbaglia
accusa. Il codice e' identico, la conseguenza no — e la mia lista di riuso
diceva «riusa `_RIFERIMENTO_RE`, non riscriverlo», che era giusto sul CODICE e
cieco sul VERSO.

🔑 **E i miei due controlli non potevano salvarmi**: verificavano la LOGICA (il
rilevatore vede? l'astensione serve?) e **nessuno dei due guardava la
POPOLAZIONE**. Le fonti del corpus sono in gran parte **tabellari** — dump di
log, tabelle a colonne — dove `righe`, `nota`, `no`, `schedule` stanno **accanto
a un numero come intestazione o unita'**, non come riferimento di sezione.
⇒ **I controlli verificano il meccanismo; solo il corpus verifica
l'applicabilita'.**

⚠️ E la stessa popolazione ha gia' ucciso **`L4.3`** stanotte (27 falsi positivi
su 28), per la **stessa** ragione: due rilevatori diversi, un solo killer. **Il
fatto che sia successo due volte non e' sfortuna: e' una proprieta' del
corpus**, e va scritta prima del prossimo tentativo.

⚠️ CONFONDENTE DICHIARATO: `facts.grounding_span` e' **troncato a 400 caratteri**
(`grounding_gate._GROUNDING_SPAN_BUDGET`). Il troncamento puo' **gonfiare** i
falsi positivi — un'occorrenza del numero fuori da una numerazione puo' essere
stata tagliata via. ⇒ Il 10/10 e' un **limite superiore** dell'errore, non la sua
misura esatta. Non cambia il verdetto (dieci su dieci sono leggibili a mano e
sbagliati per la ragione mostrata), ma cambia cosa se ne puo' concludere.

VERDETTO: **NON proponibile.** Nessuna promozione, nessun collegamento al gate.

    python docs/stato-reale/banchi/ws3-il-rilevatore-strutturale-sul-corpus-dieci-su-dieci-sbagliati.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _numero_solo_strutturale import (  # noqa: E402
    avviso_numero_solo_strutturale,
)

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)  # SOLA LETTURA
    righe = con.execute(
        "SELECT proposition, grounding_span FROM facts "
        "WHERE grounding_span IS NOT NULL AND length(grounding_span) > 0"
    ).fetchall()
    print(f"  popolazione: {len(righe)} fatti con grounding_span"
          f"  (troncato a 400 char: confondente DICHIARATO)")

    seg = [(p, s, a) for p, s in righe
           if (a := avviso_numero_solo_strutturale(p or "", s or ""))]
    print(f"  segnalati:   {len(seg)}"
          f"  ({100 * len(seg) / max(1, len(righe)):.2f}%)")

    # CONTROLLO CHE DEVE POTER FALLIRE: il rilevatore deve VEDERE. Se segnala
    # zero, un «zero falsi positivi» non sarebbe una qualita' ma un'assenza di
    # misura — e' l'errore che ho gia' fatto due volte stanotte.
    print(f"\n  [1] CONTROLLO POSITIVO — il rilevatore ha segnalato qualcosa? "
          f"{bool(seg)}")
    if not seg:
        print("      CONTROLLO CADUTO: zero segnalazioni ⇒ non distinguo «e'")
        print("      preciso» da «e' spento». NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print("     I dieci casi sono stati LETTI UNO PER UNO (non contati):")
    print("     10 falsi positivi su 10 — «righe»/«nota»/«no»/«schedule»")
    print("     agganciati come marcatori di sezione mentre erano UNITA',")
    print("     INTESTAZIONI DI COLONNA e NOMI DI EVENTO in fonti TABELLARI.")
    print("     ⇒ NON PROPONIBILE. Nessuna promozione, nessun collegamento.")
    print()
    print("     La causa non e' la regex: `_RIFERIMENTO_RE` e' nata per SALTARE")
    print("     (falso aggancio = conservativo). Riusata per ACCUSARE, lo stesso")
    print("     falso aggancio diventa un'accusa. Stesso codice, verso opposto.")
    print("     E i miei due controlli verificavano la LOGICA, non la")
    print("     POPOLAZIONE: nessuno dei due poteva vedere questo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
