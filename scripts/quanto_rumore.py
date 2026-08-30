"""Quanto rumore c'e' in una proporzione? E due numeri differiscono davvero?

    python scripts/quanto_rumore.py 29 100              -> IC95 di 29/100
    python scripts/quanto_rumore.py 29 100 34 100       -> e i due differiscono?
    python scripts/quanto_rumore.py --serve 5 --intorno 30   -> quanti casi servono

PERCHE' ESISTE. Il 30/08, dopo sei ore di misure su C10, ho calcolato per la
prima volta l'intervallo sui numeri che avevo gia' pubblicato:

    veri persi     29,0%  [21,0 - 38,5]   e  34,0%  [25,5 - 43,7]   si sovrappongono
    falsi ammessi  16,0%  [10,1 - 24,4]   e  18,0%  [11,7 - 26,7]   si sovrappongono

⇒ **Avevo speso la sera a SPIEGARE due differenze che stanno nel rumore** — una
col bias della popolazione, una col daemon di embedding — e avevo perfino
progettato e lanciato un A/B da 40 minuti per separare due cause di un effetto
che non c'e'.

⇒ 🔑 **Una proporzione senza intervallo INVITA a spiegare differenze che non
esistono.** Con ~100 casi non si distingue nulla sotto **18 punti**.

⚠️ E il colpo peggiore: avevo pubblicato *«predico entrambi entro ±7 punti»* e
poi l'avevo dichiarata centrata. **±7 sta DENTRO la barra d'errore: quella
predizione non poteva cadere.** ⇒ **Prima di impegnarsi su una soglia, va
verificato che sia FUORI dall'intervallo**, altrimenti si mette in scena il
rigore invece di farlo.

NOTA. Wilson e non l'intervallo «normale» (`p ± z·sqrt(p(1-p)/n)`): quello si
rompe agli estremi — su 0/100 darebbe `[0,0]`, cioe' «certezza assoluta» dal
campione piu' povero possibile. Wilson da' `[0,0 - 3,7]`, che e' la cosa onesta.
E' esattamente il caso che mi e' capitato con HaluMem (0 veri persi su 100).
"""
from __future__ import annotations

import argparse
import math
import sys


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervallo di Wilson in percentuale. Regge anche k=0 e k=n."""
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    semi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * max(0.0, centro - semi), 100 * min(1.0, centro + semi)


def casi_necessari(differenza: float, intorno: float, z: float = 1.96) -> int:
    """Quanti casi per faccia servono a vedere `differenza` punti attorno a `intorno`."""
    p = intorno / 100
    d = differenza / 100
    #: due proporzioni indipendenti, approssimazione normale
    return math.ceil(2 * z * z * p * (1 - p) / (d * d))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("numeri", nargs="*", type=int,
                    help="k n  (una proporzione)  oppure  k1 n1 k2 n2  (confronto)")
    ap.add_argument("--serve", type=float, help="differenza in punti che vuoi poter vedere")
    ap.add_argument("--intorno", type=float, default=30.0, help="proporzione attesa, in %%")
    a = ap.parse_args()

    if a.serve:
        n = casi_necessari(a.serve, a.intorno)
        print(f"  per vedere {a.serve:g} punti attorno al {a.intorno:g}% servono "
              f"~{n} casi PER FACCIA")
        print(f"  (con 100 casi la differenza minima visibile e' "
              f"~{(wilson(int(a.intorno), 100)[1] - wilson(int(a.intorno), 100)[0]):.0f} punti)")
        return 0

    if len(a.numeri) == 2:
        k, n = a.numeri
        lo, hi = wilson(k, n)
        print(f"  {k}/{n} = {100 * k / n:.1f}%   IC95 [{lo:.1f} , {hi:.1f}]   "
              f"ampiezza {hi - lo:.1f} punti")
        return 0

    if len(a.numeri) == 4:
        k1, n1, k2, n2 = a.numeri
        l1, h1 = wilson(k1, n1)
        l2, h2 = wilson(k2, n2)
        print(f"  A  {k1}/{n1} = {100 * k1 / n1:5.1f}%   IC95 [{l1:.1f} , {h1:.1f}]")
        print(f"  B  {k2}/{n2} = {100 * k2 / n2:5.1f}%   IC95 [{l2:.1f} , {h2:.1f}]")
        sovrapposti = not (h1 < l2 or h2 < l1)
        if sovrapposti:
            print("  ⇒ 🔴 GLI INTERVALLI SI SOVRAPPONGONO: la differenza NON e' "
                  "distinguibile dal rumore.")
            print("     Non cercarle una causa: potrebbe non esserci niente da spiegare.")
        else:
            print("  ⇒ ✅ intervalli disgiunti: la differenza e' reale a questo livello.")
        #: la sovrapposizione degli IC e' un criterio CONSERVATIVO — puo' dire
        #: «non distinguibile» quando un test a due campioni direbbe di si'.
        #: Lo dichiaro invece di far passare il verdetto per definitivo.
        print("     (criterio conservativo: la sovrapposizione degli IC e' piu' severa "
              "di un test a due campioni)")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
