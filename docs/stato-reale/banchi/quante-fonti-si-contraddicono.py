"""QUANTE DELLE NOSTRE FONTI CONTENGONO DUE VALORI PER LA STESSA CHIAVE.

\U0001f4cc **LA GRANDEZZA DEL LIMITE DI `W7-98`.** Là ho dimostrato che una
fonte che contiene sia *«318 pezzi»* sia *«250 pezzi»* **ammette ENTRAMBI i
claim** (99,98 e 97,97, `layers []`), mentre un valore assente viene fermato
(0,66) — quindi il gate era acceso. **Non viola la promessa** (la fonte
supporta davvero entrambi): e' un **limite non dichiarato**, il prodotto
controlla le contraddizioni **fra fatti**, non **dentro una fonte**.

Mancava la grandezza: **quanto e' frequente quella condizione da noi?**

\U0001f511 **PERCHE' RIGUARDA NOI PIU' DI ALTRI**: `O3` ci impone di incollare
**l'output grezzo** come fonte, e un output di terminale contiene spesso la
**stessa misura ripetuta** — due esecuzioni, un prima/dopo, una tabella con
piu' righe.

⚠️ **QUESTO BANCO NON CONTA ERRORI, CONTA UNA CONDIZIONE.** Due valori per la
stessa chiave possono essere **legittimi**: `passed=4` in un blocco e
`passed=10` in un altro sono due esecuzioni diverse, non una contraddizione.
Il banco misura **quante fonti espongono il prodotto al caso di `W7-98`**, non
quante contengano un errore. Confondere le due cose sarebbe l'errore che ho
gia' fatto stanotte tre volte.

ATTESA DICHIARATA PRIMA: **alta, sopra il 30%** — le nostre fonti sono output
di terminale. ⚠️ **Se fosse bassa, il limite e' reale ma raro** e lo dico con
la stessa forza.

CONTROLLI CHE POSSONO FALLIRE:
 (1) ⚖️ **l'euristica e' MIA e va mostrata**: `chiave=N` / `chiave: N` con la
     stessa chiave e valori diversi. Il banco stampa **esempi veri**, perche'
     chi legge possa contestarla.
 (2) 🪞 **conto a parte i casi in cui i due valori distano MOLTO** (ordini di
     grandezza): li' e' quasi certamente un prima/dopo legittimo, non una
     doppia misura della stessa cosa.
 (3) ✅ **controllo positivo**: la maggior parte delle fonti NON deve avere
     chiavi ripetute con valori diversi. Se le avesse tutte, l'euristica
     prende qualunque cosa e non misura niente.
 (4) ⚠️ **limite ereditato da `W7-90`**: `grounding_span` e' un **estratto**
     (budget 400) ⇒ misuro la condizione **nell'estratto che il giudice ha
     visto**, che e' cio' che conta per il verdetto, ma **sottostima** quella
     nel documento originale.

    python -u docs/stato-reale/banchi/quante-fonti-si-contraddicono.py
"""

from __future__ import annotations

import re
import sqlite3
import sys
from collections import defaultdict

#: (1) l'euristica, dichiarata: una parola, un separatore, un numero.
COPPIA = re.compile(r"([A-Za-z_][A-Za-z0-9_]{2,})\s*[=:]\s*(\d+(?:\.\d+)?)")


def main() -> int:
    try:
        from verimem.config import CONFIG
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = con.execute(
        "select proposition, grounding_span from facts "
        "where superseded_by is null and grounding_span is not null "
        "and grounding_span <> ''").fetchall()
    print(f"  fatti vivi con fonte: {len(righe)}")

    con_coppie = 0
    doppi: list[tuple[str, str, list[str], str]] = []
    lontani = 0
    for prop, span in righe:
        m: dict[str, set[str]] = defaultdict(set)
        for k, v in COPPIA.findall(span or ""):
            m[k.casefold()].add(v)
        if not m:
            continue
        con_coppie += 1
        for k, vs in m.items():
            if len(vs) < 2:
                continue
            # (2) due valori che distano ordini di grandezza: quasi certamente
            #     un prima/dopo, non due misure della stessa cosa.
            try:
                nn = sorted(float(x) for x in vs)
                if nn[0] > 0 and nn[-1] / nn[0] >= 100:
                    lontani += 1
                    continue
            except ValueError:
                pass
            doppi.append((prop or "", span or "", sorted(vs), k))
            break

    print(f"  …con almeno una coppia chiave=numero: {con_coppie}")
    if con_coppie < 50:
        print("NON RIUSCITO: meno di cinquanta fonti con coppie: l'euristica")
        print("non trova la forma che cerco su questo corpus.")
        return 1

    quota = 100.0 * len(doppi) / con_coppie
    print(f"\n  == LA CONDIZIONE DI `W7-98`: {len(doppi)} fonti su"
          f" {con_coppie}  ({quota:.1f}%)")
    print(f"     (esclusi {lontani} casi in cui i due valori distano 100x o"
          " piu': prima/dopo)")

    # (3) il controllo che deve poter fallire
    if quota > 90.0:
        print("\n     CADUTO (controllo 3): quasi tutte le fonti hanno chiavi")
        print("     ripetute con valori diversi. L'euristica prende qualunque")
        print("     cosa e il numero non misura niente.")
        return 1

    print("\n  -- (1) SEI ESEMPI VERI, perche' l'euristica sia contestabile")
    for prop, span, vs, k in doppi[:6]:
        print(f"\n     chiave «{k}» con valori {vs}")
        print(f"       claim: {prop[:88]}")
        print(f"       fonte: {span[:150].replace(chr(10), ' | ')}")

    print("\n  == LA RIGA CHE CONTA")
    if quota >= 30.0:
        print(f"     🔴 **{quota:.1f}% delle nostre fonti espone il prodotto al"
              " caso di")
        print("     `W7-98`**: contengono due valori per la stessa chiave, e"
              " su una")
        print("     fonte cosi' **il gate ammette qualunque delle due versioni"
              " senza")
        print("     avvisare che l'altra esiste**.")
        print("     ⚠️ **NON dice che siano errori**: due esecuzioni diverse"
              " nello")
        print("     stesso incollaggio sono legittime. Dice che **la"
              " condizione e'")
        print("     la norma, non l'eccezione**, e che il limite va scritto.")
    elif len(doppi) > 5:
        print(f"     🟡 **{quota:.1f}%**: la condizione esiste ma non e' la"
              " norma. Il limite")
        print("     di `W7-98` e' reale e **circoscritto**.")
    else:
        print(f"     🟢 **{quota:.1f}%**: quasi nessuna fonte. Il caso di"
              " `W7-98` e'")
        print("     costruito e **non tocca il nostro corpus** — lo dico con la")
        print("     stessa forza con cui avrei annunciato il contrario.")

    print("\n  ⚠️ COSA NON DICE: l'euristica vede **una sola forma**"
          " (`chiave=numero`):")
    print("  una contraddizione in prosa non la vede · **non distingue"
          " l'errore")
    print("  dalla ripetizione legittima**, e non e' il suo compito ·"
          " e `grounding_span`")
    print("  e' un ESTRATTO (`W7-90`), quindi questo **sottostima** la"
          " condizione")
    print("  nel documento originale.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
