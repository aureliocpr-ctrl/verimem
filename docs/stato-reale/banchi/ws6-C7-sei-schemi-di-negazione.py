# -*- coding: utf-8 -*-
r"""C7 NEGAZIONI E ASSENZE: il 20,8% era della CLASSE o del mio unico schema?

Alle 20:50 ho misurato che una fonte che nega il claim viene ammessa 5 volte su 24
(IT 2/12, EN 3/12) - ma con **un solo** schema di negazione, e l'avevo dichiarato come
il limite principale. Qui gli schemi sono sei, i soggetti sei (tre per lingua), le
lunghezze tre: 108 celle di negazione, piu' i due controlli.

PREDIZIONE DICHIARATA PRIMA DI ESEGUIRE, e viene dal meccanismo che @ws4 ha nominato
alle 20:49 («il giudice la vede e le da' segno invertito») unito al mio dato
(fonte NEUTRA 0,08 · fonte che NEGA 99,91: e' la frase che nega a PRODURRE il punteggio):
  se cio' che conta e' la **sovrapposizione di superficie** col claim, allora
  · schemi che RICALCANO il claim (non-X, zero-X, ha smesso di X) -> piu' errori
  · schema 4 «e' vuoto», che non nomina ne' il verbo ne' l'oggetto -> **quasi nessun
    errore**, perche' col claim non condivide quasi nulla
  Se invece lo schema 4 sbaglia quanto gli altri, **il meccanismo non e' la
  sovrapposizione** e la mia spiegazione cade.

RISULTATO (27/08 21:08, questo file, 108 celle di negazione + 36 di controllo):

   AMMESSE PER ERRORE, per SCHEMA (18 celle ciascuno)
      1 NON         **0 su 18**      <- l'unico che regge SEMPRE
      2 ZERO          8 su 18
      3 ASSENZA       9 su 18
      4 STATO       **12 su 18**     <- il PEGGIORE, ed e' quello che ricalca MENO
      5 SOSTITUZ      8 su 18
      6 CESSAZ        9 su 18
   per LINGUA: IT 30 su 54 · EN 16 su 54        TOTALE **46 su 108 = 42,6%**

⛔ LA MIA PREDIZIONE E' FALSIFICATA, E NELLA DIREZIONE OPPOSTA. Avevo predetto che lo
schema 4 («e' vuoto»), che col claim non condivide ne' verbo ne' oggetto, sarebbe stato
il piu' correttamente rifiutato. E' il PEGGIORE di tutti (12 su 18). ⇒ **La
sovrapposizione di superficie NON e' il meccanismo**, e la spiegazione che avevo dato
alle 21:05 cade. E' la quarta mia ipotesi che muore in questo laboratorio.

🔑 IL PATTERN VERO, e non l'avevo previsto: **l'unico modo di negare che il gate
riconosce e' quello con la particella negativa esplicita** («non» / «does not»): 0 errori
su 18. Gli altri cinque modi di dire esattamente la stessa cosa passano dal 44% al 67%
delle volte, con punteggi 96-99,99 - **cioe' quelli di un sostegno pieno**.

🔴 E IL RIEMPITIVO E' CIO' CHE ROMPE IL GIUDIZIO. Senza riempitivo il gate regge quasi
sempre; con 100 o 200 parole di testo che del soggetto NON PARLA, crolla:
      riempitivo    0 parole  ->  ~4 errori su 36
      riempitivo  100 parole  -> ~21 errori su 36
      riempitivo  200 parole  -> ~22 errori su 36
⇒ **Aggiungere alla fonte del testo irrilevante fa passare la negazione.** E' il fatto
che un utente incontra sempre: una fonte vera non e' mai una frase sola.

CONTROLLI, entrambi reggono ⇒ il difetto e' specifico e il banco non e' rotto:
   A (la fonte SOSTIENE) ... 95,71 - 99,99 in tutte e 18 le celle
   C (fonte NEUTRA) ........ 0,06 - 0,47 in tutte e 18 ⇒ nessuna inflazione generale

⚠️ SULLA LINGUA NON CONCLUDO. IT 30/54 contro EN 16/54 sembra una differenza, ma
guardando i soggetti e' di nuovo **per-soggetto**: in inglese GAMMA sbaglia quasi
ovunque e OMEGA quasi mai. Tre soggetti per lingua non bastano a separare le due cose,
e stasera ho gia' preso questo abbaglio una volta.
📏 LIMITE: sei soggetti scritti da me, tre lunghezze, un solo documento di riempimento.
Il 42,6% e' il tasso su QUESTA popolazione: non e' il tasso del corpus.

I SEI SCHEMI (ogni frase e' scritta a mano nelle due lingue, non tradotta a macchina):
  1 NON esplicita        «non elenca le misure»
  2 QUANTIFICATORE ZERO  «elenca zero misure»
  3 ASSENZA              «le misure sono assenti»
  4 STATO                «e' vuoto»                  <- non nomina verbo ne' oggetto
  5 SOSTITUZIONE         «elenca soltanto i costi del personale»
  6 CESSAZIONE           «ha smesso di elencare le misure»

CONTROLLI, perche' una popolazione sola direbbe che ogni criterio e' ottimo:
  A la fonte SOSTIENE  -> deve restare alta
  C la fonte e' NEUTRA -> deve restare al pavimento (0,0x): se sale, il difetto non e'
    della negazione ma un'inflazione generale, e questo banco non dice niente.

REGIME: `Memory(path=...)` su store temporaneo · FUORI da pytest (dove l'embedder e' uno
stub SHA-256) · un solo processo · riempitivo = `docs/BENCHMARKS.md`, documento vero ·
warm-up di due write buttati · soglia in uso dichiarata dal prodotto stesso a ogni
avvio: `validated local CE moat cut 40`.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-C7-sei-schemi-di-negazione.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RIEMP = [0, 100, 200]
SCHEMI = ["1 NON", "2 ZERO", "3 ASSENZA", "4 STATO", "5 SOSTITUZ", "6 CESSAZ"]

SOGGETTI = [
    ("IT", "Il registro ALFA elenca le misure del progetto.", [
        "Il registro ALFA non elenca le misure del progetto.",
        "Il registro ALFA elenca zero misure del progetto.",
        "Nel registro ALFA le misure del progetto sono assenti.",
        "Il registro ALFA e' vuoto.",
        "Il registro ALFA elenca soltanto i costi del personale.",
        "Il registro ALFA ha smesso di elencare le misure del progetto.",
    ]),
    ("IT", "Il deposito DELTA contiene le forniture invernali.", [
        "Il deposito DELTA non contiene le forniture invernali.",
        "Il deposito DELTA contiene zero forniture invernali.",
        "Nel deposito DELTA le forniture invernali sono assenti.",
        "Il deposito DELTA e' vuoto.",
        "Il deposito DELTA contiene soltanto attrezzi da giardino.",
        "Il deposito DELTA ha smesso di contenere le forniture invernali.",
    ]),
    ("IT", "Il collaudo EPSILON copre tutti i moduli consegnati.", [
        "Il collaudo EPSILON non copre i moduli consegnati.",
        "Il collaudo EPSILON copre zero moduli consegnati.",
        "Nel collaudo EPSILON i moduli consegnati sono assenti.",
        "Il collaudo EPSILON e' vuoto.",
        "Il collaudo EPSILON copre soltanto la documentazione interna.",
        "Il collaudo EPSILON ha smesso di coprire i moduli consegnati.",
    ]),
    ("EN", "The GAMMA ledger lists the project measurements.", [
        "The GAMMA ledger does not list the project measurements.",
        "The GAMMA ledger lists zero project measurements.",
        "In the GAMMA ledger the project measurements are absent.",
        "The GAMMA ledger is empty.",
        "The GAMMA ledger lists only the staff costs.",
        "The GAMMA ledger has stopped listing the project measurements.",
    ]),
    ("EN", "The OMEGA warehouse holds the winter supplies.", [
        "The OMEGA warehouse does not hold the winter supplies.",
        "The OMEGA warehouse holds zero winter supplies.",
        "In the OMEGA warehouse the winter supplies are absent.",
        "The OMEGA warehouse is empty.",
        "The OMEGA warehouse holds only garden tools.",
        "The OMEGA warehouse has stopped holding the winter supplies.",
    ]),
    ("EN", "The KAPPA review covers every delivered module.", [
        "The KAPPA review does not cover the delivered modules.",
        "The KAPPA review covers zero delivered modules.",
        "In the KAPPA review the delivered modules are absent.",
        "The KAPPA review is empty.",
        "The KAPPA review covers only the internal documentation.",
        "The KAPPA review has stopped covering the delivered modules.",
    ]),
]


def main() -> None:
    parole = (REPO / "docs" / "BENCHMARKS.md").read_text(encoding="utf-8").split()
    from verimem.client import Memory
    mem = Memory(str(Path(tempfile.mkdtemp()) / "c7.db"))
    for i in range(2):
        mem.add(f"Il registro WARMUP{i} elenca le misure.", topic="c7/warmup",
                source=f"Il registro WARMUP{i} elenca le misure.")

    def g(claim, src, topic):
        r = mem.add(claim, topic=topic, source=src) or {}
        return (r.get("grounding", r.get("grounding_score")), r.get("status", "?"))

    per_schema = {s: [0, 0] for s in SCHEMI}
    per_lingua = {"IT": [0, 0], "EN": [0, 0]}
    print("celle: la fonte NEGA il claim -> 'quarantined' e' il giudizio CORRETTO\n")
    for si, (ling, claim, neg) in enumerate(SOGGETTI):
        print(f"--- {ling}  {claim}")
        for ri, R in enumerate(RIEMP):
            coda = " ".join(parole[:R])
            ga, _ = g(claim, f"{claim}\n\n{coda}".strip(), f"c7/A{si}-{R}")
            gc, _ = g(claim, coda or "Un testo che di questo non parla.", f"c7/C{si}-{R}")
            righe = []
            for k, n in enumerate(neg):
                gb, sb = g(claim, f"{n}\n\n{coda}".strip(), f"c7/B{si}-{ri}-{k}")
                bad = sb != "quarantined"
                per_schema[SCHEMI[k]][0] += 1
                per_schema[SCHEMI[k]][1] += 1 if bad else 0
                per_lingua[ling][0] += 1
                per_lingua[ling][1] += 1 if bad else 0
                righe.append(f"{SCHEMI[k][0]}:{gb:6.2f}{'!' if bad else ' '}")
            print(f"   riemp {R:>4}  A={ga:6.2f} C={gc:5.2f}  |  " + " ".join(righe))

    print("\n=== AMMESSE PER ERRORE, per SCHEMA (su 18 celle ciascuno) ===")
    for s in SCHEMI:
        n, bad = per_schema[s]
        print(f"   {s:<12} {bad:>2} su {n}")
    print("=== per LINGUA (su 54 celle ciascuna) ===")
    for l in ("IT", "EN"):
        n, bad = per_lingua[l]
        print(f"   {l} {bad:>2} su {n}")
    tot = sum(v[1] for v in per_schema.values())
    print(f"=== TOTALE {tot} su {sum(v[0] for v in per_schema.values())}")


if __name__ == "__main__":
    main()
