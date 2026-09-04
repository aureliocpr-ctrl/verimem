"""LIVELLO: il giudice locale (`get_local_judge`), un processo solo, un caricamento solo.

MURO 1 · P6-③: quanto costa giudicare N claim atomici per M frasi di fonte,
invece di una coppia sola.

    python docs/stato-reale/banchi/ws3-muro1-P6c-quanto-costa-giudicare-a-pezzi.py [N_COPPIE]

⚠️ RICHIEDE UNO SLOT (carica il modello). Store di Aurelio in SOLA LETTURA:
serve solo a pescare testi VERI e tutti DIVERSI.

━━ PREDIZIONE DEPOSITATA (402605cc10e18db6, P6-③) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    «l'atomico costa >= 2x l'intero, perche' fa N giudizi invece di uno.»
    🔴 muore sotto 2x: allora il costo non e' proporzionale ai pezzi e c'e' un
    percorso caldo che non avevo considerato.
Il percorso caldo esiste ed e' proprio qui: `LocalGroundingJudge.score` chiama
`self._ensure_scorer()([coppia])[0]` — lo scorer prende gia' una LISTA di coppie
e dentro fa i lotti da 32. Quindi le N x M coppie di una scrittura possono
partire in UNA chiamata. Se il lotto paga, la mia P6-③ muore, e muore bene:
vuol dire che la cura del lead costa meno di quanto temevo.

━━ COME SI MISURA SENZA INGANNARSI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
· UN SOLO PROCESSO e un solo caricamento: ieri un mio 12,30x era gonfiato
  perche' confrontavo due impianti diversi.
· COPPIE SEMPRE DIVERSE: ripetere lo stesso input misura la cache, non la
  latenza (e' l'errore che ho fatto e corretto in P4/P5).
· il caricamento del modello e la prima chiamata stanno FUORI dalla misura,
  dichiarati a parte: sono un costo per processo, non per scrittura.
· il costo si riporta PER COPPIA, cosi' si puo' moltiplicare per la forma vera
  di una scrittura (N unita' x M frasi) invece di leggere un rapporto solo.

━━ MISURATO il 04/09 alle 21:38 e alle 21:42 (due esecuzioni) ━━━━━━━━━━━━━━━━
    caricamento del modello   26,0 s / 26,7 s   (per PROCESSO, non per scrittura)
    prima chiamata (scalda)    2,15 s /  2,08 s  (esclusa)

    una coppia per volta      64,2 / 65,1 ms per coppia
    lotto da  2               27,5 / 25,6 ms       2,33x / 2,54x
    lotto da  4               13,2 / 12,9 ms       4,86x / 5,03x
    lotto da  8                6,2 /  6,9 ms      10,39x / 9,43x
    lotto da 16                5,3 /  5,3 ms      12,06x / 12,40x
    lotto da 32                5,7 /  5,7 ms      11,29x / 11,35x   <- satura a 16

    COSTO DI UNA SCRITTURA, in multipli del giudizio intero:
       coppie    seriale    in un lotto solo
          2       2,00x         0,79x
          4       4,00x         0,80x
          9       9,00x         0,95x
         12      12,00x         1,27x

🔴 **P6-③ E' FALSIFICATA, e muore bene.** Avevo predetto «>= 2x»: in un lotto solo
   il rapporto sta fra 0,79x e 1,27x, e per la forma tipica (2 unita' x 1 frase)
   e' **0,79x — MENO del giudizio intero**. Il percorso caldo che non avevo
   considerato e' l'overhead per CHIAMATA: due coppie insieme costano meno di una
   coppia da sola. La cura del lead, implementata in lotto, e' gratis.

⇒ E c'e' un guadagno che non dipende dalla decomposizione: oggi il prodotto
  giudica UNA coppia per volta e paga 65 ms; sedici coppie insieme ne costano 85.
  Chi possiede il percorso di scrittura puo' prendersi quel margine comunque.

━━ PERCHE' I NUMERI SOPRA SONO CONSERVATIVI (il costo vero e' piu' basso) ━━━━━
① la colonna «in un lotto solo» usa il lotto MISURATO piu' piccolo che ci sta:
   3 coppie leggono il costo del lotto da 2, 6 quello del lotto da 4. Un lotto
   della misura giusta costerebbe meno per coppia — quindi 1,18x e 1,27x sono
   sovrastime, non misure.
② entrambi i bracci usano gli STESSI testi interi: nella realta' i pezzi atomici
   sono piu' CORTI di una frase intera, e il costo di un transformer cresce con
   la lunghezza. L'atomico vero costerebbe ancora meno.
Nessuna delle due aggiustature l'ho applicata: preferisco un numero che sbaglia
CONTRO la conclusione che sto sostenendo.

━━ CIO' CHE QUESTO BANCO NON DICE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il numero di coppie per scrittura e' N x M: N lo conosco (2,03 unita' medie sul
corpus con la regex corretta), M no — le fonti non stanno nel corpus, solo la
loro firma. Quindi qui misuro il costo PER COPPIA e la curva del lotto; il
costo per scrittura si ottiene moltiplicando, e M resta dichiarato come non
misurato invece di essere inventato.
"""
from __future__ import annotations

import pathlib
import random
import sqlite3
import sys
import time

ALBERO = pathlib.Path(r"C:\Users\aurel\Code\HippoAgent")
sys.path.insert(0, str(ALBERO))

import verimem  # noqa: E402
from verimem.local_grounding import get_local_judge  # noqa: E402

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
SEED = 20260904


def testi_veri(quanti: int) -> list[str]:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL "
            "AND proposition IS NOT NULL AND LENGTH(proposition) BETWEEN 60 AND 400")
            if r[0]]
    finally:
        con.close()
    random.Random(SEED).shuffle(righe)
    return righe[:quanti]


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 128
    print("IMPORT DA", verimem.__file__)

    testi = testi_veri(2 * n + 64)
    coppie = [(testi[2 * i], testi[2 * i + 1]) for i in range(n)]
    print(f"coppie VERE e tutte diverse: {len(coppie)}  (seed {SEED})\n")

    t0 = time.perf_counter()
    judge = get_local_judge()
    scorer = judge._ensure_scorer()  # noqa: SLF001 — e' il percorso che `score` usa
    carico = time.perf_counter() - t0

    # la prima chiamata scalda: fuori dalla misura, ma DICHIARATA
    t0 = time.perf_counter()
    scorer([judge.coppia(*coppie[-1])])
    prima = time.perf_counter() - t0
    print(f"caricamento del modello : {carico:7.2f} s   (per processo, non per scrittura)")
    print(f"prima chiamata (scalda) : {prima:7.3f} s   (esclusa dalle misure sotto)\n")

    misure: dict[int, float] = {}
    for k in (1, 2, 4, 8, 16, 32):
        usate = coppie[:max(1, (n // k) * k)]
        lotti = [usate[i:i + k] for i in range(0, len(usate), k)]
        t0 = time.perf_counter()
        for lotto in lotti:
            scorer([judge.coppia(s, f) for s, f in lotto])
        dt = time.perf_counter() - t0
        misure[k] = dt / len(usate)
        print(f"  lotto da {k:2d}: {len(usate):4d} coppie in {dt:6.2f} s"
              f"  ->  {1000 * misure[k]:7.1f} ms per coppia"
              f"   ({misure[1] / misure[k]:4.2f}x rispetto a una per volta)"
              if k > 1 else
              f"  UNA PER VOLTA: {len(usate):4d} coppie in {dt:6.2f} s"
              f"  ->  {1000 * misure[k]:7.1f} ms per coppia")

    print("\nCOSTO DI UNA SCRITTURA, in multipli del giudizio intero (1 coppia):")
    print("   coppie      seriale        in un lotto solo")
    for n_coppie in (2, 3, 4, 6, 9, 12):
        # il lotto piu' grande che ci sta: 3 coppie viaggiano come un lotto da 2
        # piu' una, e il costo per coppia si legge da quello misurato piu' vicino
        k = max(x for x in misure if x <= n_coppie)
        seriale = n_coppie * misure[1]
        lotto = n_coppie * misure[k]
        print(f"     {n_coppie:2d}      {seriale / misure[1]:5.2f}x"
              f"          {lotto / misure[1]:5.2f}x   (lotto da {k})")
    print("\n  ⇒ P6-③ diceva «>= 2x». Con il lotto il rapporto e' quello della")
    print("    colonna di destra: se sta sotto 2 per le forme comuni, la mia")
    print("    predizione e' FALSIFICATA e la cura costa meno di quanto temevo.")
    print("  ⚠️ N x M per scrittura: N = 2,03 unita' medie (misurato), M = frasi")
    print("    della fonte, NON misurato — le fonti non stanno nel corpus.")


if __name__ == "__main__":
    main()
