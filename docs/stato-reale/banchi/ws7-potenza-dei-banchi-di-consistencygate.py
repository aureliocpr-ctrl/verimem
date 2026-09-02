"""Con 50 e 41 coppie, il confronto con ConsistencyGate puo' concludere qualcosa?

PERCHE'. @lead-audit (02/09 12:50) porta ConsistencyGate (arxiv 2607.22962,
25/07/2026) come campo diverso per M1: e' l'unico paper che pubblica i nostri
stessi due assi e ha rilasciato i suoi banchi. I loro numeri:

  MemContam      sintetico, 1000 veri + 1000 falsi   50,0% -> 1,2%   veri persi 0%
  LoCoMo-Contam  conversazioni reali, 50 probe pair  50,0% -> 34,1%  veri persi 42%
  MSC-Contam     41 probe pair                       50,0% -> 36,7%  veri persi 7%
  il nostro C10  su dataset DIVERSO                  50,0% -> 15,9%  veri persi 29,3%

Il lead dichiara gia' il limite: «LoCoMo-Contam e MSC-Contam sono minuscoli — gli
intervalli saranno larghi, e va detto». Questo banco quantifica QUANTO larghi
**prima** di eseguire, perche' il controllo che puo' falsificarti va fatto prima.

⚠️ IL PUNTO DEL BANCO NON E' DIRE «NON SI PUO' FARE». E' dire su QUALE banco il
confronto puo' concludere, cosi' che l'esperimento venga disegnato di conseguenza
invece di produrre quattro numeri che nessuno puo' usare.

🪞 E USO DUE RIGHELLI, non uno. La sovrapposizione degli intervalli di Wilson e'
un criterio CONSERVATIVO: dice «non distinguibile» piu' spesso del dovuto. Il
test esatto di Fisher e' piu' potente. Se usassi solo il primo, dichiarerei
non-concludibile qualcosa che invece conclude — e sarebbe la quinta volta in due
giorni che un mio righello sbaglia CONTRO di noi.
"""
import sys
from math import comb


def fisher_due_code(a: int, b: int, c: int, d: int) -> float:
    """p esatto a due code per la tabella 2x2 [[a,b],[c,d]], senza scipy."""
    n = a + b + c + d
    riga1, col1 = a + b, a + c

    def p_tab(x: int) -> float:
        return (comb(riga1, x) * comb(n - riga1, col1 - x)) / comb(n, col1)

    p_oss = p_tab(a)
    lo = max(0, col1 - (n - riga1))
    hi = min(riga1, col1)
    #: due code = somma di tutte le tabelle non piu' probabili di quella osservata
    return min(1.0, sum(p_tab(x) for x in range(lo, hi + 1)
                        if p_tab(x) <= p_oss * (1 + 1e-9)))


#: (etichetta, k_loro, n_loro, k_nostro, n_nostro)
CONFRONTI = [
    ("LoCoMo-Contam · falsita' ammessa  34,1% vs 15,9%", 17, 50, 8, 50),
    ("LoCoMo-Contam · veri persi        42,0% vs 29,3%", 21, 50, 15, 50),
    ("MSC-Contam    · falsita' ammessa  36,7% vs 15,9%", 15, 41, 7, 41),
    ("MSC-Contam    · veri persi         7,0% vs 29,3%", 3, 41, 12, 41),
    ("MemContam     · falsita' ammessa   1,2% vs 15,9%", 12, 1000, 159, 1000),
]


def main() -> int:
    print("  I due righelli a confronto. Il nostro valore e' IPOTETICO: e' il")
    print("  numero del C10 trasportato sulla loro n, per chiedersi se una")
    print("  differenza di quella taglia sarebbe VISIBILE con quel campione.\n")
    print(f"  {'confronto':<52} {'Fisher p':>10}   verdetto")
    concludibili = []
    for eti, k1, n1, k2, n2 in CONFRONTI:
        p = fisher_due_code(k1, n1 - k1, k2, n2 - k2)
        ok = p < 0.05
        if ok:
            concludibili.append(eti)
        print(f"  {eti:<52} {p:>10.4f}   {'✅ conclude' if ok else '🔴 non conclude'}")

    print(f"\n  ⇒ confronti che possono concludere: {len(concludibili)} su {len(CONFRONTI)}")
    for c in concludibili:
        print(f"       {c}")
    print("\n  ⚠️ E il Fisher e' il righello PIU' POTENTE dei due: se non conclude")
    print("     qui, non conclude nemmeno con la sovrapposizione degli intervalli.")
    print("  ⚠️ Questi p valgono per una differenza DELLA TAGLIA IPOTIZZATA. Il")
    print("     nostro numero vero sui loro banchi non lo conosco: va misurato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
