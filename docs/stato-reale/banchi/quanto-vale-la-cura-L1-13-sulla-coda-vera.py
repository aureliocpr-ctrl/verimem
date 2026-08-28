"""QUANTO VALE LA CURA DI `L1.13` SUI 1074 QUARANTINATI VIVI — e cosa NON puo' valere.

Chiudendo la cella W7-32 avevo dichiarato un «non dico»: «*quanti dei 1073 in
coda di quarantena sarebbero riammessi da questa cura e' una misura che non ho
fatto*». Questa e' quella misura.

⚠️ E la prima cosa che dice non e' un numero, e' un VINCOLO: la tabella `facts`
ha 31 colonne e **nessuna contiene la source**. Ci sono `source_signature` (una
firma, non il testo) e `grounding_span` (un frammento). ⇒ **La cura non e'
retroattiva per costruzione**, e la domanda giusta non e' «quanti ne riammette»
ma:

  ① QUANTI dei quarantinati vivi sono fermati da `L1.13`?   (la taglia)
  ② Di quelli, quanti conservano un `grounding_span`?        (cio' che resta)
  ③ Su quanti il participio compare DENTRO quello span?      (il recuperabile)

Il ③ e' un LIMITE INFERIORE del recuperabile, non una stima: uno span e' un
frammento, e il participio potrebbe stare nella fonte fuori dal frammento.

CONTROLLI CHE POSSONO FALLIRE:
 (1) se zero quarantinati portano un warning `L1.13`, il difetto che ho curato
     non ha taglia su questo corpus e lo dico invece di cercarne un'altra.
 (2) se `grounding_span` e' vuoto su TUTTI, il ③ e' zero per costruzione e va
     letto come «non misurabile con cio' che e' stato conservato», non come
     «nessuno e' recuperabile».
 (3) il detector si riesegue: e' deterministico e non chiama modelli. Se
     l'import fallisce, il banco lo dice invece di misurare il vuoto.

    python -u docs/stato-reale/banchi/quanto-vale-la-cura-L1-13-sulla-coda-vera.py
"""

from __future__ import annotations

import sqlite3
import sys


def main() -> int:
    try:
        from verimem.config import CONFIG
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    db = str(CONFIG.semantic_db)
    print(f"  db: {db}")
    con = sqlite3.connect(db)
    righe = list(con.execute(
        "SELECT id, proposition, quarantined_by, grounding_span "
        "FROM facts WHERE status='quarantined' AND superseded_by IS NULL"))
    print(f"  quarantinati vivi: {len(righe)}")
    if not righe:
        print("  NON RIUSCITO: nessuna riga, non ho misurato niente.")
        return 1

    con_l113 = []          # ① fermati da L1.13 (detector rieseguito)
    con_span = []          # ② di quelli, con uno span non vuoto
    recuperabili = []      # ③ di quelli, col participio DENTRO lo span
    for _id, prop, qb, span in righe:
        w = detect_unsupported_completion_claim(
            proposition=prop or "", verified_by=[])
        if w is None:
            continue
        con_l113.append((_id, prop, w.matched_text, span))
        if span:
            con_span.append((_id, prop, w.matched_text, span))
            if w.matched_text.casefold() in str(span).casefold():
                recuperabili.append((_id, prop, w.matched_text, span))

    n = len(righe)
    print(f"\n  == I TRE NUMERI, su {n} quarantinati vivi")
    print(f"     ① fermati da L1.13 (detector rieseguito) : {len(con_l113)}"
          f"   ({100.0 * len(con_l113) / n:.1f}%)")
    print(f"     ② di quelli, con grounding_span non vuoto: {len(con_span)}")
    print(f"     ③ col participio DENTRO lo span          : {len(recuperabili)}")

    print("\n  -- CONTROLLO (1): il difetto curato ha taglia su questo corpus?")
    if not con_l113:
        print("     CADUTO - zero quarantinati portano un warning L1.13: la cura")
        print("     non ha effetto su questa coda, qualunque cosa dica il resto.")
        return 1
    print(f"     retto - {len(con_l113)} righe portano un warning L1.13")

    print("\n  -- CONTROLLO (2): lo span e' conservato?")
    if not con_span:
        print(f"     Zero span su {len(con_l113)}: il ③ e' zero PER COSTRUZIONE.")
        print("     Si legge «non misurabile con cio' che e' stato conservato»,")
        print("     NON «nessuno e' recuperabile».")
    else:
        print(f"     {len(con_span)} righe su {len(con_l113)} conservano uno span")

    print("\n  -- UN CAMPIONE dei fermati da L1.13, per vedere la forma")
    for _id, prop, mt, span in con_l113[:6]:
        print(f"     [{mt}]  {str(prop)[:78]}")

    if recuperabili:
        print("\n  -- E dei RECUPERABILI (participio dentro lo span)")
        for _id, prop, mt, span in recuperabili[:4]:
            print(f"     [{mt}]  {str(prop)[:70]}")
            print(f"          span: {str(span)[:70]}")

    print("\n  == COSA QUESTO NUMERO NON DICE")
    print("     La source completa NON e' fra le colonne di `facts`: ci sono")
    print("     `source_signature` (una firma) e `grounding_span` (un")
    print("     frammento). ⇒ La cura vale per le scritture FUTURE, e per la")
    print("     coda esistente il ③ e' un LIMITE INFERIORE: il participio puo'")
    print("     stare nella fonte fuori dal frammento conservato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
