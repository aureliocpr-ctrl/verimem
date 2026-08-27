# -*- coding: utf-8 -*-
r"""Una fonte che NEGA il claim viene ammessa 5 volte su 24 — e non e' la lingua.

RISULTATO (27/08 20:47, build 19d7e6ea, questo file, tre lunghezze x otto claim):

  IT   Il registro ALFA elenca le misure...      100p  78.54 | 150p   1.67 | 200p  95.84 AMMESSA
       La stazione BETA registra la temperatura  100p   3.29 | 150p   2.83 | 200p   7.05
       Il deposito DELTA contiene le forniture   100p   1.50 | 150p   0.71 | 200p   1.49
       Il collaudo EPSILON copre tutti i moduli  100p   3.20 | 150p  73.58 | 200p  99.36 AMMESSA
  EN   The GAMMA ledger lists the project meas.  100p  99.91 | 150p  99.80 | 200p  99.91 AMMESSA x3
       The SIGMA station records the temperature 100p   0.48 | 150p   0.23 | 200p   0.10
       The OMEGA warehouse holds the winter sup. 100p   0.31 | 150p   0.15 | 200p   0.42
       The KAPPA review covers every delivered   100p   3.19 | 150p   2.60 | 200p   0.30
  ⇒ IT 2 su 12 · EN 3 su 12 · TOTALE **5 su 24 = 20,8%**

⇒ **NON E' LA LINGUA**: era la mia ipotesi dopo il giro precedente (dove l'unico claim
inglese sbagliava cinque volte su cinque) ed e' **falsa**. Con quattro claim per lingua
la differenza sparisce. E' la TERZA mia ipotesi che cade in questo laboratorio: prima il
costo che doveva crescere con la lunghezza (e' piatto), poi il troncamento posizionale
(non c'e'), ora la lingua.

🔑 CIO' CHE RESTA MISURATO, ed e' peggio di tutte e tre:
· quando il giudice sbaglia **non e' incerto: e' sicuro**. I cinque errori valgono
  95.84 · 99.36 · 99.91 · 99.80 · 99.91, contro il 99.98 di una fonte che sostiene
  davvero. **Il punteggio di un errore e' indistinguibile da quello di un sostegno.**
· il comportamento e' **bimodale**: o vede (0.1-3.3) o non vede (95-99.9). In mezzo,
  quasi nulla. Non e' una soglia da tarare: e' un interruttore che a volte si gira.
· `GAMMA` sbaglia su **tutte e tre** le lunghezze, `SIGMA`/`OMEGA` mai — stessa lingua,
  stessa struttura, stesso schema di negazione. **La variabile e' il claim, e non so
  quale sua proprieta' sia.** Lo dichiaro invece di inventarne una.

CONTROLLI (una popolazione sola avrebbe detto che va tutto bene):
· A, la fonte che SOSTIENE, resta 96-99.99 in tutte le celle: il verso positivo regge.
· C, una fonte NEUTRA che del soggetto non parla, resta **0.06-0.09 ovunque**: il gate
  non e' inflazionato in generale, e a 200 parole non ammette qualunque cosa. Il difetto
  e' specifico della NEGAZIONE, che condivide col claim quasi tutte le parole.

IL LIMITE, che e' un debito e non un'assicurazione: otto claim, tre lunghezze, **un solo
schema di negazione** («non ... nessun ... e' vuoto»). Le celle non sono indipendenti fra
loro. Il 20,8% e' il tasso su QUESTA popolazione costruita da me: non e' il tasso del
corpus, e chi lo cita come tale lo sta gonfiando.

REGIME: `Memory(path=...)` su store temporaneo · FUORI da pytest (dove l'embedder e' uno
stub SHA-256) · un solo processo · riempitivo = `docs/BENCHMARKS.md`, documento vero ·
warm-up di due write buttati, perche' i modelli si caricano in due scalini.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-la-fonte-che-nega-viene-ammessa.py
"""
from __future__ import annotations
import tempfile
from pathlib import Path

REPO = Path(r"C:\Users\aurel\Code\HippoAgent")
D = [100, 150, 200]
IT = [
    ("Il registro ALFA elenca le misure del progetto.",
     "Il registro ALFA non elenca nessuna misura: e' vuoto, e del progetto non conserva niente."),
    ("La stazione BETA registra la temperatura ogni ora.",
     "La stazione BETA non registra nessuna temperatura: e' spenta da mesi e non produce dati."),
    ("Il deposito DELTA contiene le forniture invernali.",
     "Il deposito DELTA non contiene nessuna fornitura: e' stato svuotato e resta vuoto."),
    ("Il collaudo EPSILON copre tutti i moduli consegnati.",
     "Il collaudo EPSILON non copre nessun modulo: non e' mai stato eseguito su niente."),
]
EN = [
    ("The GAMMA ledger lists the project measurements.",
     "The GAMMA ledger lists no measurement at all: it is empty and keeps nothing of the project."),
    ("The SIGMA station records the temperature every hour.",
     "The SIGMA station records no temperature at all: it has been off for months and produces nothing."),
    ("The OMEGA warehouse holds the winter supplies.",
     "The OMEGA warehouse holds no supply at all: it was emptied and stays empty."),
    ("The KAPPA review covers every delivered module.",
     "The KAPPA review covers no module at all: it was never carried out on anything."),
]


def main() -> None:
    parole = (REPO / "docs" / "BENCHMARKS.md").read_text(encoding="utf-8").split()
    from verimem.client import Memory
    mem = Memory(str(Path(tempfile.mkdtemp()) / "ling.db"))
    for i in range(2):
        mem.add(f"Il registro WARMUP{i} elenca le misure.", topic="ling/warmup",
                source=f"Il registro WARMUP{i} elenca le misure.")

    def g(claim, src, topic):
        r = mem.add(claim, topic=topic, source=src) or {}
        return r.get("grounding", r.get("grounding_score")), r.get("status", "?")

    tot = {"IT": [0, 0], "EN": [0, 0]}
    for ling, coppie in (("IT", IT), ("EN", EN)):
        print(f"\n=== {ling} — la fonte NEGA il claim; quarantined = giudizio CORRETTO")
        for k, (claim, nega) in enumerate(coppie):
            righe = []
            for L in D:
                coda = " ".join(parole[:L])
                gb, sb = g(claim, f"{nega}\n\n{coda}", f"ling/{ling}{k}-{L}")
                ok = sb == "quarantined"
                tot[ling][0] += 1
                tot[ling][1] += 0 if ok else 1
                righe.append(f"{L}p:{gb:7.2f}{'' if ok else ' AMMESSA'}")
            print(f"  {claim[:46]:<46} " + " | ".join(righe))
    print()
    for ling in ("IT", "EN"):
        n, bad = tot[ling]
        print(f"  {ling}: negazioni AMMESSE (errore) {bad} su {n} celle")


main()
