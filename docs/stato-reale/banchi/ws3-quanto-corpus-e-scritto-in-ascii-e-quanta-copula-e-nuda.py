"""LIVELLO: solo regex sul corpus vivo, in SOLA LETTURA. Nessun gate, nessun modello.

Due buchi ortografici trovati stanotte, e il loro DENOMINATORE — senza il quale
nessuna delle due cure ha una priorita'.

    python docs/stato-reale/banchi/ws3-quanto-corpus-e-scritto-in-ascii-e-quanta-copula-e-nuda.py

⚡ COSTO ZERO, < 30 s.

━━ I DUE BUCHI, con il banco che li ha trovati ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ① LE FORME ASCII DELL'ACCENTO. Il giudice legge «è» meglio di «e'»: +0,04 di
     AUROC su 4 celle su 4 (ws3-il-giudice-legge-e-accentata-ed-e-apostrofo…).
     W7-73 contava 976 «e'» contro 357 «è». Ma «e'» non e' l'unica forma: puo',
     da', sara', cosi', piu', perche', gia', ne', se', cioe', poiche', finche'.
     Domanda: quanti fatti VIVI contengono almeno una forma ASCII — cioe' quanti
     verrebbero giudicati diversamente da una normalizzazione prima del giudice?
  ② LA COPULA NUDA. Nei QUALI del campione C (ws3-decomponi-contro-lo-splitter…)
     «La frase che dice che non e chiaro se il modulo…» e' stata spezzata su
     « e chiaro »: la «e» copula scritta senza accento ne' apostrofo viene letta
     come congiunzione. La memoria dice che «e» copula e' gia' una strada
     falsificata altrove (nel gate): qui la domanda e' solo QUANTO capita, per
     decidere se lo splitter deve proteggersi.
     Righello: « e » seguita da un participio/aggettivo di stato tipico
     (chiaro, vero, falso, pronto, finito, completo, verificato, stato, giusto,
     sbagliato, vuoto, pieno, rosso, verde, aperto, chiuso) o da «un/una/il/la»
     NON e' una prova di copula — e' un TETTO: conta anche «rosso e verde».
     Si stampa il tetto e un campione da leggere, non un tasso.

━━ PREDIZIONI, scritte prima (06/09 00:02) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    H1 i fatti vivi con almeno una forma ASCII sono >= 40% del corpus (W7-73
       dava «e'» in ~1.000 fatti; le altre forme si sommano). 🔴 muore sotto 25%.
    H2 il tetto della copula nuda e' < 3% del corpus: e' un buco raro e lo
       splitter puo' dichiararlo senza curarlo. 🔴 muore sopra 5%.

━━ ESITO, 06/09 00:04-00:10, corpus vivo 15.378 fatti ━━━━━━━━━━━━━━━━━━━━━━━━━
  ① forme ASCII dell'accento
       con almeno una forma ASCII        1.372   8,9%    <- il denominatore della cura
       con almeno un accento vero          717   4,7%
       SOLO ASCII                        1.359   8,8%  · miste 13 (0,1%)
       per forma: e' 1026 · piu' 179 · da' 154 · gia' 119 · perche' 91 · E' 76 ·
                  puo' 45 · cioe' 36 · ne' 28 · finche' 24
     H1 (>= 40%): 🔴 FALSIFICATA — e mi corregge in pubblico: nel banco delle
     grafie e nel post 27cde06ecc5d8c43 avevo scritto «il giudice lavora sul lato
     debole nel 73% delle scritture». Il 73% e' 976 contro 357 FRA le scritture
     che hanno una copula scritta; sul corpus intero la cura «normalizza prima
     del giudice» tocca l'8,9% dei fatti. Numeratore senza denominatore, la
     forma piu' comune di numero vero che inganna. Corretto dove stava.
  ② la copula nuda («non e chiaro»), tre righelli in dieci minuti:
       con articoli e stati               1.822  11,85%   campione: ~5/10 copule
       con numeri e stati                 1.772  11,52%   campione:  2/10 copule
       SOLO stati                           188   1,22%   campione:  8/10 copule
     H2 (< 3%): REGGE col terzo righello. I primi due erano RUMORE DEL MISURATORE
     («e il commit» e «e 3 file di test» sono congiunzioni): un criterio vale
     solo se il campione letto lo conferma. Stima onesta: ~1% del corpus, cioe'
     la meta' del buco « ed » (2,0%). Lo splitter puo' DICHIARARLO senza curarlo:
     spezzare su una copula nuda produce un frammento in ~1 fatto su 100.
⇒ Priorita' che ne esce, coi numeri: normalizzare le forme ASCII prima del
  giudice tocca 1.372 fatti (+0,04 di AUROC ciascuno); proteggere lo splitter
  dalla copula nuda ne tocca ~150. La prima e' la cura; la seconda e' una riga
  nel docstring di decomponi().
"""
from __future__ import annotations

import random
import re
import sqlite3

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"

FORME_ASCII = ["e'", "E'", "puo'", "da'", "sara'", "cosi'", "piu'", "perche'", "gia'",
               "ne'", "se'", "cioe'", "poiche'", "finche'", "verita'", "attivita'",
               "funzionalita'", "novita'", "citta'", "qualita'", "capacita'"]
_ASCII = re.compile(r"(?<![\w'])(?:" + "|".join(re.escape(f) for f in FORME_ASCII) + r")(?=\s|$|[.,;:!?)])")
_ACCENTI = re.compile(r"[èàìòùÈ]")
# la copula nuda: « e » seguita da uno stato/participio tipico o da un NUMERO
# («il clean_admit_rate e 0.917», «ed e il 14,3 per cento»). Primo righello,
# 06/09 00:04: conteneva anche gli articoli (un/una/il/la…) e dava 11,85% — ma
# «e il commit e' a0fbe104» e' una congiunzione: un righello che non distingue
# «e il» copula da «e il» congiunzione non e' un tetto, e' rumore. Tolti.
_COPULA_NUDA = re.compile(
    r"(?<![\w'])e\s+(?:chiaro|chiara|vero|vera|falso|falsa|pronto|pronta|finito|finita|"
    r"completo|completa|verificato|verificata|stato|stata|giusto|giusta|sbagliato|"
    r"sbagliata|vuoto|vuota|pieno|piena|rosso|rossa|verde|aperto|aperta|chiuso|chiusa|"
    r"uguale|diverso|diversa|identico|identica|presente|assente|attivo|attiva|"
    r"spento|spenta|acceso|accesa|morto|morta|vivo|viva|nullo|nulla)\b")
# Secondo righello (00:07): con i NUMERI dopo « e » dava 11,52% — ma «10 file py
# e 3 file di test» e' una congiunzione: nel campione 2 copule su 10. Tolti anche
# i numeri. Terzo righello = solo STATI: e' il tetto piu' stretto che una regex
# possa dare; il numero vero sta fra questo e la lettura del campione.


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL AND proposition IS NOT NULL") if r[0]]
    finally:
        con.close()
    tot = len(righe)

    con_ascii = [t for t in righe if _ASCII.search(t)]
    con_accenti = [t for t in righe if _ACCENTI.search(t)]
    solo_ascii = [t for t in con_ascii if not _ACCENTI.search(t)]
    miste = [t for t in con_ascii if _ACCENTI.search(t)]
    per_forma = {f: sum(1 for t in righe if re.search(r"(?<![\w'])" + re.escape(f) + r"(?=\s|$|[.,;:!?)])", t))
                 for f in FORME_ASCII}

    print(f"① LE FORME ASCII DELL'ACCENTO — corpus vivo {tot} fatti")
    print(f"   con almeno una forma ASCII      : {len(con_ascii):6d}  ({100 * len(con_ascii) / tot:.1f}%)")
    print(f"   con almeno un accento vero      : {len(con_accenti):6d}  ({100 * len(con_accenti) / tot:.1f}%)")
    print(f"   SOLO ASCII (nessun accento)     : {len(solo_ascii):6d}  ({100 * len(solo_ascii) / tot:.1f}%)")
    print(f"   miste (ASCII e accenti insieme) : {len(miste):6d}  ({100 * len(miste) / tot:.1f}%)")
    print("   per forma (fatti che la contengono):")
    for f, k in sorted(per_forma.items(), key=lambda x: -x[1])[:10]:
        print(f"     {f:16s} {k:6d}")
    h1 = 100 * len(con_ascii) / tot
    print(f"   ⇒ H1 (>= 40%): {'REGGE' if h1 >= 40 else ('🔴 FALSIFICATA' if h1 < 25 else 'indeciso')}")

    tetto = [t for t in righe if _COPULA_NUDA.search(t)]
    print("\n② LA COPULA NUDA — tetto (conta anche «rosso e verde»)")
    print(f"   fatti che matchano il righello  : {len(tetto):6d}  ({100 * len(tetto) / tot:.2f}%)")
    h2 = 100 * len(tetto) / tot
    print(f"   ⇒ H2 (< 3%): {'REGGE' if h2 < 3 else ('🔴 FALSIFICATA' if h2 > 5 else 'indeciso')}")
    print("   campione da LEGGERE (10 a caso, con il pezzo che matcha):")
    random.Random(7).shuffle(tetto)
    for t in tetto[:10]:
        m = _COPULA_NUDA.search(t)
        i = max(0, m.start() - 35)
        print(f"     · …{t[i:m.end() + 25].replace(chr(10), ' ')}…")


if __name__ == "__main__":
    main()
