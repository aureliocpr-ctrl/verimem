# -*- coding: utf-8 -*-
"""F1 · La finestra giusta e' la FRASE o l'ARTICOLO? Misurato sulle fonti VERE.

Nel design doc (`F1-DESIGN-DOC-strato-soggetto-valore.md`) ho dichiarato due
cose non verificate. Questa e' la seconda, e decide se il meccanismo funziona:

  «la segmentazione in frasi: su un contratto vero le "frasi" sono ARTICOLI, e
   un articolo puo' contenere DUE valori legati a DUE soggetti. Se la finestra
   e' la frase sbagliata, il passo 3 dice OK a uno scambio. Non ho misurato
   quanto spesso accade, e non lo stimo.»

Il passo 3 di `L4.3` dice: «se le ancore del claim toccano una frase che
contiene il valore, allora OK». **Se una sola frase contiene DUE valori della
STESSA UNITA' legati a soggetti DIVERSI, quel passo assolve uno scambio** —
perche' il soggetto giusto e quello sbagliato stanno nella stessa finestra.

⇒ questa NON e' la cura: e' la misura di una sua PRECONDIZIONE, e si fa sui
  dati veri, non sui miei esempi. Nessuna riga di prodotto viene toccata.

DOVE MISURO: `grounding_span` sullo store reale — i frammenti di fonte che il
prodotto ha DAVVERO usato per giudicare, in SOLA LETTURA (`mode=ro`).
⚠️ Il percorso lo chiedo al prodotto (`CONFIG.semantic_db`), non all'intuito:
   il percorso ovvio e' un database VUOTO (lezione in memoria).

LA PREDIZIONE, scritta prima di eseguire:
  la quota di frasi con >=2 valori della stessa unita' e' SOTTO il 10%.
  Se e' sopra il 25%, la finestra-frase e' inadeguata e il passo 3 va
  ridisegnato PRIMA di scrivere la cura, non dopo.

CONTROLLO CHE DEVE POTER FALLIRE: se l'estrattore di valori trovasse zero
valori su tutto il corpus, non starei misurando le finestre ma un regex rotto.
Il banco si ferma e non stampa una quota.

    python docs/stato-reale/banchi/ws3-F1-la-finestra-e-la-frase-o-l-articolo.py
"""

from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter

# valore + unita' attaccata: percentuali, valute, unita' di misura, date
_VAL = re.compile(
    r"(?P<num>\d[\d.,]*)\s*(?P<uni>%|euro|eur|€|mg|ml|g\b|kg|giorni|mesi|anni|"
    r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|"
    r"ottobre|novembre|dicembre)",
    re.I,
)
_FRASE = re.compile(r"(?<=[.;:!?])\s+")


def _unita(u: str) -> str:
    u = u.lower()
    if u in ("euro", "eur", "€"):
        return "valuta"
    if u in ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
             "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"):
        return "data"
    return u


def main() -> int:
    from verimem.config import CONFIG  # noqa: PLC0415

    db = str(CONFIG.semantic_db)
    print("  REGIME, dichiarato E misurato:")
    print(f"    store: {db}")
    print("    SOLA LETTURA (mode=ro) · nessuna scrittura · store di Aurelio")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT grounding_span FROM facts WHERE grounding_span IS NOT NULL "
            "AND length(grounding_span) > 0")]
    finally:
        con.close()
    print(f"    frammenti di fonte (grounding_span non nulli): {len(righe)}")
    print("    ⚠️ lo span e' TRONCATO a 400 caratteri dal prodotto (reperto di")
    print("       @ws7/@ws1): misuro finestre dentro un testo gia' tagliato.")

    n_frasi = 0
    con_val = 0
    multi_stessa_unita = 0
    multi_unita_diverse = 0
    valori_tot = 0
    esempi = []
    unita_c: Counter[str] = Counter()

    for span in righe:
        for frase in _FRASE.split(span):
            frase = frase.strip()
            if not frase:
                continue
            n_frasi += 1
            trovati = [(m.group("num"), _unita(m.group("uni")))
                       for m in _VAL.finditer(frase)]
            if not trovati:
                continue
            con_val += 1
            valori_tot += len(trovati)
            for _n, u in trovati:
                unita_c[u] += 1
            per_unita: dict[str, set[str]] = {}
            for num, u in trovati:
                per_unita.setdefault(u, set()).add(num)
            if any(len(v) >= 2 for v in per_unita.values()):
                multi_stessa_unita += 1
                if len(esempi) < 4:
                    esempi.append(frase[:150])
            elif len(per_unita) >= 2:
                multi_unita_diverse += 1

    # ── controllo che deve poter fallire ────────────────────────────────
    print(f"\n  CONTROLLO: valori trovati in tutto il corpus: {valori_tot}")
    if valori_tot == 0:
        print("     CONTROLLO CADUTO: zero valori ⇒ sto misurando un regex rotto,")
        print("     non le finestre. NESSUNA QUOTA.")
        return 1

    print(f"\n  ══ LE FINESTRE ══")
    print(f"     frasi totali .............................. {n_frasi}")
    print(f"     frasi con almeno un valore ................ {con_val}"
          f"   ({100 * con_val / max(n_frasi, 1):.1f}% del totale)")
    if con_val:
        q_stessa = 100 * multi_stessa_unita / con_val
        q_div = 100 * multi_unita_diverse / con_val
        print(f"     ► con >=2 valori della STESSA unita' ...... {multi_stessa_unita}"
              f"   ({q_stessa:.1f}% di quelle con un valore)")
        print(f"       con >=2 valori di unita' DIVERSE ........ {multi_unita_diverse}"
              f"   ({q_div:.1f}%)")
    print(f"     unita' piu' frequenti: "
          f"{', '.join(f'{u}={c}' for u, c in unita_c.most_common(6))}")

    if esempi:
        print("\n  ESEMPI di frasi con due valori della stessa unita'")
        print("  (sono i casi in cui il PASSO 3 assolverebbe uno scambio):")
        for e in esempi:
            print(f"     · {re.sub(r'[^ -~à-ù]', '?', e)}")

    print("\n  ══ VERDETTO sulla PREDIZIONE ══")
    q = 100 * multi_stessa_unita / max(con_val, 1)
    print(f"     previsto: SOTTO il 10%   ·   misurato: {q:.1f}%")
    if q < 10:
        print("     PREDIZIONE RETTA: la finestra-frase e' adeguata sulla grande")
        print("     maggioranza delle fonti vere. Il passo 3 regge, e il caso")
        print("     patologico resta una minoranza da dichiarare come limite.")
    elif q < 25:
        print("     PREDIZIONE SBAGLIATA nella taglia: la quota e' sopra il 10%.")
        print("     Il passo 3 regge sulla maggioranza ma la minoranza NON e'")
        print("     trascurabile: va dichiarata come falso-negativo atteso.")
    else:
        print("     PREDIZIONE FALSIFICATA: la finestra-frase e' INADEGUATA.")
        print("     Il passo 3 va ridisegnato PRIMA di scrivere la cura.")
    print("\n  ⚠️ LIMITI: lo span e' troncato a 400 caratteri dal prodotto, quindi")
    print("     le frasi lunghe possono essere tagliate a meta' ⇒ la quota qui")
    print("     e' verosimilmente una SOTTOSTIMA. La segmentazione e' una regex")
    print("     su punteggiatura: un «Art. 3» la spezza dove non dovrebbe.")
    print("     Un corpus solo, quello di Aurelio, in un solo istante.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
