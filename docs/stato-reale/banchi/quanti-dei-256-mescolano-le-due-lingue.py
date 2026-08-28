"""QUANTI DEI 256 MESCOLANO LE DUE LINGUE — la famiglia che la cura non raggiunge.

La popolazione di controllo (W7-36) ha trovato il limite della cura del 28/08:
perdona solo cio' che la fonte scrive **alla lettera**, quindi un claim italiano
(«*il job e' **finito***») con una fonte CI in inglese (`completed/failure`)
resta fermato — **e il layer ha ragione**, perche' quel participio nella fonte
non c'e'.

Quanto e' grande quella famiglia? ⚠️ **Non posso misurarla sulla coppia
claim-fonte**: la source non e' persistita. Misuro un suo PROXY diretto —
**quanti claim mescolano le due lingue DENTRO la proposizione stessa**: un testo
italiano il cui participio di completamento e' una parola inglese, o viceversa.

🪞 ⚠️ **E IL PROXY MISURA L'OPPOSTO DI CIO' PER CUI L'AVEVO SCELTO — me ne sono
accorta leggendo gli esempi, dopo averlo eseguito.** I casi che trova sono
claim italiani col participio **gia' inglese** («*il job risulta
**completed**/success*»): li' il claim RICOPIA il referto, quindi il participio
**e'** nella fonte e **la cura FUNZIONA**. La famiglia problematica e' quella
che **TRADUCE** — «*il job e' **finito***» per una fonte che dice `completed` —
e quella **non e' contabile da qui**, perche' richiede di sapere in che lingua
e' la FONTE, che non e' persistita.

⇒ Cio' che questo banco misura davvero e' quindi: **quanti dei 256 la cura
letterale COPRE grazie al fatto che il claim ha gia' ricopiato la parola**. E'
un numero utile, ma e' il complemento di quello che cercavo. Il banco resta
com'e', con questa riga sopra: il risultato vale, la domanda no.

CONTROLLI CHE POSSONO FALLIRE:
 (1) se il rilevatore di lingua classifica quasi tutto «incerto», non separa
     niente e il numero non vale: lo dico invece di pubblicarlo.
 (2) le due popolazioni: misuro la mescolanza **anche** sui quarantinati che
     `L1.13` NON ferma. Se la quota e' la stessa, la mescolanza non e' un
     tratto dei 256 — e' un tratto del corpus, e non spiega niente.

    python -u docs/stato-reale/banchi/quanti-dei-256-mescolano-le-due-lingue.py
"""

from __future__ import annotations

import re
import sqlite3
import sys

# Parole funzionali: grezze ma dichiarate, e contate su ENTRAMBE le lingue.
_IT = re.compile(r"\b(?:il|lo|la|i|gli|le|un|una|di|del|della|dei|delle|che|"
                 r"e'|non|per|con|nel|nella|sono|era|erano|alle|dal|dalla|"
                 r"questo|questa|piu'|dopo|prima|sul|sulla)\b", re.IGNORECASE)
_EN = re.compile(r"\b(?:the|of|is|are|was|were|and|for|with|from|this|that|"
                 r"has|have|been|not|but|all|its|on|at|by|as|it)\b",
                 re.IGNORECASE)

# Le parole del detector, divise per lingua.
_PAROLE_IT = {"completato", "completata", "completati", "completate", "completo",
              "completa", "completi", "complete_it", "finito", "finita",
              "finiti", "finite", "chiuso", "chiusa", "chiusi", "chiuse",
              "concluso", "conclusa", "conclusi", "concluse", "fatto", "fatta",
              "fatti", "fatte"}
_PAROLE_EN = {"complete", "completed", "done", "finished", "closed",
              "wrapped-up", "wrapped up", "all-done", "all done", "task-done",
              "task done"}


def lingua(testo: str) -> str:
    it, en = len(_IT.findall(testo or "")), len(_EN.findall(testo or ""))
    if it == 0 and en == 0:
        return "incerto"
    if it >= 2 * max(1, en):
        return "IT"
    if en >= 2 * max(1, it):
        return "EN"
    return "incerto"


def lingua_parola(mt: str) -> str:
    k = (mt or "").casefold()
    if k in _PAROLE_IT:
        return "IT"
    if k in _PAROLE_EN:
        return "EN"
    return "?"


def main() -> int:
    try:
        from verimem.config import CONFIG
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = [r[0] for r in con.execute(
        "SELECT proposition FROM facts "
        "WHERE status='quarantined' AND superseded_by IS NULL")]
    print(f"  db: {CONFIG.semantic_db}")
    print(f"  quarantinati vivi: {len(righe)}")

    fermati, non_fermati = [], []
    for p in righe:
        w = detect_unsupported_completion_claim(proposition=p or "",
                                                verified_by=[])
        (fermati if w else non_fermati).append((p, w.matched_text if w else None))

    def conta(gruppo, con_parola):
        misti = incerti = 0
        esempi = []
        for p, mt in gruppo:
            lt = lingua(p or "")
            if lt == "incerto":
                incerti += 1
                continue
            if not con_parola:
                continue
            lp = lingua_parola(mt)
            if lp == "?":
                continue
            if lp != lt:
                misti += 1
                if len(esempi) < 5:
                    esempi.append((lt, mt, p))
        return misti, incerti, esempi

    n = len(fermati)
    misti, incerti, esempi = conta(fermati, True)
    print(f"\n  == I 256 CHE `L1.13` FERMA — sono {n}")
    print(f"     lingua incerta                  : {incerti}")
    print(f"     claim in una lingua, PARTICIPIO nell'altra: {misti}"
          f"   ({100.0 * misti / max(1, n):.1f}%)")
    for lt, mt, p in esempi:
        print(f"       [claim {lt} · participio «{mt}»]  {str(p)[:62]}")

    print("\n  -- CONTROLLO (1): il rilevatore di lingua separa?")
    if incerti > 0.6 * n:
        print(f"     CADUTO - {incerti} su {n} sono «incerti»: il rilevatore non")
        print("     classifica, e la percentuale sopra non significa niente.")
        return 1
    print(f"     retto - {n - incerti} su {n} classificati")

    print("\n  -- CONTROLLO (2): la mescolanza e' un tratto dei 256 o del corpus?")
    # sui NON fermati non c'e' un participio: misuro solo la lingua, per vedere
    # se la popolazione di fondo e' altrettanto mista.
    lingue_fondo = {}
    for p, _ in non_fermati:
        lingue_fondo[lingua(p or "")] = lingue_fondo.get(lingua(p or ""), 0) + 1
    tot_f = sum(lingue_fondo.values())
    print(f"     lingua dei {tot_f} quarantinati NON fermati da L1.13:")
    for k, v in sorted(lingue_fondo.items(), key=lambda x: -x[1]):
        print(f"        {k:<8} {v:>5}  ({100.0 * v / max(1, tot_f):.1f}%)")
    lingue_256 = {}
    for p, _ in fermati:
        lingue_256[lingua(p or "")] = lingue_256.get(lingua(p or ""), 0) + 1
    print(f"     lingua dei {n} fermati da L1.13:")
    for k, v in sorted(lingue_256.items(), key=lambda x: -x[1]):
        print(f"        {k:<8} {v:>5}  ({100.0 * v / max(1, n):.1f}%)")
    print("\n     ⚖️ Le due distribuzioni si confrontano a occhio qui sopra: se")
    print("     sono uguali, la lingua NON e' un tratto dei 256. Il numero che")
    print("     conta e' comunque quello dei MISTI, che sui non-fermati non")
    print("     esiste (non c'e' participio da confrontare) — e questo e' un")
    print("     limite del confronto, non un risultato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
