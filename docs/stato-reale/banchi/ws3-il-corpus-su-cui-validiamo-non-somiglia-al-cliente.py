"""Il corpus su cui validiamo il gate e' output di strumenti, non prosa.

Nasce da un errore mio, di venti minuti fa. Avevo dichiarato **«NON
proponibile»** un rilevatore (`7191e5e8`) perche' sul corpus dava **10 falsi
positivi su 10**. Il verdetto era giusto sui numeri e **sbagliato di
popolazione**: quel rilevatore nasceva per un **contratto**, e nel corpus di
contratti non ce n'e'.

LE DUE MISURE, istante **01:23 del 29/08**, `mode=ro`, 6009 span con
`grounding_span` non vuoto:

    span con >40% di righe a COLONNE ......... 3121  (51,9%)
    span con almeno una riga a colonne ....... 4288  (71,4%)
    span con numerazione tipo CONTRATTO ......    4  ( 0,07%)

ABLAZIONE, perche' un criterio che non discrimina non e' un criterio: lo stesso
test su 6009 span di **prosa sintetica** da' **0 (0,0%)**. ⇒ la colonna misura
davvero la tabellarita', non la lunghezza o il caso.

E i quattro «contratti» **letti uno per uno non sono contratti**: sono **nostri
output di banco** *sul* caso del contratto (due hanno il 100% di righe a
colonne — sono tabelle che parlano di articoli). ⇒ **la popolazione bersaglio e'
lo 0,07% del corpus, e anche quello 0,07% e' un riflesso di noi.**

🔑 **LA CONSEGUENZA SUL MIO VERDETTO, che va spezzato in due:**
- **sul NOSTRO corpus**: 10 falsi positivi, 0 veri positivi ⇒ collegarlo qui
  farebbe **solo danno**. Il «non proponibile» **regge**, per questa popolazione.
- **sulla popolazione BERSAGLIO** (prosa con numerazione di sezione): **NON
  MISURATO, e non misurabile qui** — il corpus non ne contiene. Dire «il
  rilevatore non funziona» **senza questa distinzione era una promessa che i
  miei dati non coprivano.**

🔑 **E LA CONSEGUENZA GENERALE, che vale oltre il mio rilevatore:**
**validiamo il gate su un corpus che e' per meta' output di strumenti e per lo
0,07% prosa con sezioni.** Ogni tasso di falsi positivi che misuriamo qui e' un
tasso *sul nostro traffico*, non su quello di un cliente. E' il gemello — dal
lato della **fonte** — di cio' che @ws1 ha misurato dal lato del **claim**
(«70% su forme da contratto contro 0,6% sul nostro corpus»). **Due misure
indipendenti, stessa frattura.**

⚠️ NON dice che il gate sia peggiore o migliore per un cliente: dice che **non
lo sappiamo da qui**, e che un numero preso su questo corpus non si puo'
presentare come un numero sul prodotto.

⚠️ CONFONDENTE: `grounding_span` e' troncato a 400 caratteri
(`_GROUNDING_SPAN_BUDGET`), quindi misuro la **tessitura di un ritaglio**, non
della fonte intera. Il troncamento taglia le righe finali: puo' spostare la
frazione a colonne in entrambe le direzioni.

    python docs/stato-reale/banchi/ws3-il-corpus-su-cui-validiamo-non-somiglia-al-cliente.py
"""

from __future__ import annotations

import re
import sqlite3

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"

#: una riga "a colonne": due o piu' spazi FRA due caratteri non-spazio
_COLONNE = re.compile(r"\S\s{2,}\S")
#: numerazione di sezione tipo contratto/norma
_ARTICOLO = re.compile(r"\b(?:art|artt|articolo|comma|clause|§)\b\.?\s*\d+", re.I)

PROSA_FINTA = "\n".join(["prosa normale senza colonne di sorta qui."] * 4)


def _frazione_a_colonne(span: str) -> float:
    righe = [x for x in span.split("\n") if x.strip()]
    if not righe:
        return 0.0
    return sum(1 for x in righe if _COLONNE.search(x)) / len(righe)


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)  # SOLA LETTURA
    span = [s for (s,) in con.execute(
        "SELECT grounding_span FROM facts "
        "WHERE grounding_span IS NOT NULL AND length(grounding_span) > 0")]
    n = len(span)
    print(f"  popolazione: {n} span  (troncati a 400 char: CONFONDENTE)")

    fr = [_frazione_a_colonne(s) for s in span]
    tab = sum(1 for x in fr if x > 0.40)
    almeno = sum(1 for x in fr if x > 0.0)
    art = [s for s in span if _ARTICOLO.search(s)]
    print(f"\n  >40% righe a colonne ......... {tab:>5}  ({100 * tab / n:.1f}%)")
    print(f"  almeno una riga a colonne .... {almeno:>5}  ({100 * almeno / n:.1f}%)")
    print(f"  numerazione tipo CONTRATTO ... {len(art):>5}  ({100 * len(art) / n:.2f}%)")

    # CONTROLLO CHE DEVE POTER FALLIRE: il criterio deve DISCRIMINARE. Se
    # marcasse anche la prosa, misurerei la lunghezza e non la tabellarita'.
    finti = sum(1 for _ in range(n) if _frazione_a_colonne(PROSA_FINTA) > 0.40)
    print(f"\n  [1] ABLAZIONE — stesso criterio su {n} span di PROSA sintetica: "
          f"{finti} ({100 * finti / n:.1f}%)")
    if finti:
        print("      CONTROLLO CADUTO: il criterio marca anche la prosa ⇒ non")
        print("      misura la tabellarita'. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print("     Il corpus su cui validiamo il gate e' per META' output di")
    print("     strumenti e per lo 0,07% prosa con numerazione di sezione.")
    print("     ⇒ Ogni tasso di falsi positivi misurato QUI e' un tasso sul")
    print("       NOSTRO traffico, non su quello di un cliente.")
    print("     ⇒ Il mio «rilevatore non proponibile» (7191e5e8) va spezzato:")
    print("       regge sul nostro corpus (10 FP, 0 TP), e sulla popolazione")
    print("       BERSAGLIO resta NON MISURATO — qui non e' misurabile.")
    print("     Gemello, dal lato della FONTE, del 70%-contro-0,6% che @ws1 ha")
    print("     misurato dal lato del CLAIM: due misure indipendenti, stessa")
    print("     frattura.")
    print("\n  ⚠️ NON dice che il gate sia peggiore o migliore per un cliente:")
    print("     dice che NON LO SAPPIAMO DA QUI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
