"""L'ANNO di una data inglese copre un numero inventato? — l'ipotesi, misurata.

Nel referto `bf3d696e` avevo scritto, **dichiarandola non misurata**:

    extract_quantities(«The deadline is March 12, 2027.», come_fonte=True)
        ->  [('', 2027.0)]
    ⚠️ IPOTESI: un claim che inventa «2027» riferito ad altro troverebbe 2027
       fra i valori della fonte e L4.1 tacerebbe. Non l'ho provato al gate.

Il difetto gemello — i numeri d'ARTICOLO — l'ho dichiarato solo **dopo** l'A/B
alla porta (`c9380232`, poi curato in `29ab5544`). **Stesso metro qui**: o la
misuro, o resta un'ipotesi.

MECCANISMO CANDIDATO: `_DATA_RE` cattura «March 12» ma **non l'anno**, quindi
`2027` esce dalla soppressione e finisce fra le quantità **senza unità**. Da lì
in poi è indistinguibile da qualunque altro numero nudo — che è esattamente ciò
che accadeva con «Art. 4» → `('', 4.0)`.

A/B A VARIABILE SINGOLA: stessa fonte, stesso modello di frase, cambia **solo
la cifra**. Il claim è **inventato in tutti i casi** (la fonte non parla di
unità di prodotto).

    coperto    la cifra coincide con l'ANNO di una data della fonte
    scoperto   una cifra estranea, dello stesso ordine di grandezza

LA PREDIZIONE, scritta prima di eseguire:
    scoperto -> quarantinato, L4.1 parla
    coperto  -> AMMESSO oppure L4.1 muto        <- il falso negativo

CONDIZIONE DI FALSIFICAZIONE: se anche i «coperti» sono quarantinati con L4.1
che parla, l'anno non copre niente e **l'ipotesi cade** — e va detto, perché
l'avevo pubblicata io.

CONTROLLO CHE DEVE POTER FALLIRE: i claim VERI restano ammessi, altrimenti sto
misurando un gate rotto e non un buco.

REGIME: un processo, store temporaneo vuoto, porta SDK, validate='full', EN.
Strati letti da `warnings` (la ricevuta non ha una chiave `layers`: cella 50).

    python docs/stato-reale/banchi/ws3-l-anno-inglese-copre-un-numero-inventato.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

FONTE = (
    "The delivery deadline is March 12, 2027. "
    "The review meeting is scheduled for July 4, 2031. "
    "The late-delivery penalty is 2% of the contract value per week. "
    "The contract value is 148000 euro."
)

#: (etichetta, cifra, coincide con un anno della fonte?)
CASI = [
    ("coperto  2027 ", "2027", True),
    ("coperto  2031 ", "2031", True),
    ("scoperto 2044 ", "2044", False),
    ("scoperto 1987 ", "1987", False),
    ("scoperto 3129 ", "3129", False),
]
MODELLO = "The contract covers {} units of product."

VERI = [
    "The late-delivery penalty is 2% of the contract value per week.",
    "The contract value is 148000 euro.",
]


def _strati(ric) -> list[str]:
    return [str(w.get("layer")) for w in (ric.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415
    from verimem.quantity_match import extract_quantities  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)} · python {sys.version.split()[0]}")
    print("    store TEMPORANEO vuoto · un processo · porta SDK · "
          "validate='full' · INGLESE")

    vf = sorted(extract_quantities(FONTE, come_fonte=True))
    nudi = sorted(n for u, n in vf if u == "")
    print(f"\n  [0] valori che il prodotto estrae dalla FONTE: {vf}")
    print(f"      con unita' VUOTA: {nudi}")
    if not nudi:
        print("      CONTROLLO CADUTO: nessun numero nudo nella fonte ⇒ il")
        print("      meccanismo candidato non esiste qui. NESSUN VERDETTO.")
        return 1

    mem = Memory(str(Path(tempfile.mkdtemp()) / "anno.db"))

    print("\n  [1] CONTROLLO: i claim VERI restano ammessi")
    for prop in VERI:
        r = mem.add(prop, topic=f"anno/vero/{abs(hash(prop)) % 999}",
                    source=FONTE, validate="full")
        st = str(r.get("status"))
        print(f"      {st:<12} ground={r.get('grounding_score')}  {prop[:50]}")
        if st == "quarantined":
            print("      CONTROLLO CADUTO: un VERO e' quarantinato ⇒ gate rotto,")
            print("      non un buco. NESSUN VERDETTO.")
            return 1

    print(f"\n  [2] {'caso':<15} {'esito':<14} {'ground':>7}  strati")
    print("      " + "-" * 62)
    righe = []
    for et, cifra, coperto in CASI:
        claim = MODELLO.format(cifra)
        r = mem.add(claim, topic=f"anno/{cifra}", source=FONTE, validate="full")
        st = str(r.get("status"))
        g = r.get("grounding_score")
        ls = _strati(r)
        righe.append((et, coperto, st != "quarantined",
                      any("L4.1" in x for x in ls),
                      float(g) if g is not None else -1.0))
        print(f"      {et:<15} "
              f"{'AMMESSO' if st != 'quarantined' else 'quarantinato':<14} "
              f"{float(g or -1):7.1f}  {','.join(ls) if ls else '-'}")

    cop = [r for r in righe if r[1]]
    sco = [r for r in righe if not r[1]]
    l41_cop = sum(1 for r in cop if r[3])
    l41_sco = sum(1 for r in sco if r[3])
    print("\n  ══ LE DUE POPOLAZIONI ══")
    print(f"     COPERTI  (cifra = ANNO di una data)  ammessi "
          f"{sum(1 for r in cop if r[2])}/{len(cop)}   L4.1 parla su {l41_cop}/{len(cop)}")
    print(f"     SCOPERTI (cifra estranea)            ammessi "
          f"{sum(1 for r in sco if r[2])}/{len(sco)}   L4.1 parla su {l41_sco}/{len(sco)}")

    print("\n  ══ VERDETTO ══")
    # ⚠️ Si confrontano le QUOTE, non i conteggi. La prima stesura diceva
    # `l41_sco > l41_cop` e dopo la cura stampava ancora «IPOTESI RETTA»
    # con 2 su 2 contro 3 su 3 — due volte il 100% — solo perche' 3 > 2.
    # Il banco misurava bene e RIFERIVA male: e' il difetto nel misuratore,
    # e su un presidio che qualcun altro rieseguira' e' il piu' costoso.
    q_cop = l41_cop / max(len(cop), 1)
    q_sco = l41_sco / max(len(sco), 1)
    if q_sco > q_cop:
        print("     IPOTESI RETTA: l'ANNO di una data inglese copre un numero")
        print("     INVENTATO, come faceva il numero d'articolo prima di 29ab5544.")
    elif q_cop == q_sco:
        print("     IPOTESI FALSIFICATA: L4.1 si comporta allo stesso modo sulle")
        print("     due popolazioni ⇒ l'anno non copre niente, e l'ipotesi che")
        print("     avevo pubblicato in bf3d696e VA RITIRATA.")
    else:
        print("     RISULTATO INVERSO, da spiegare: L4.1 parla PIU' sui coperti.")

    print("\n  ⚠️ LIMITI: una fonte sola, cinque casi, INGLESE, un solo modello di")
    print("     frase. Il verdetto complessivo dipende anche dal GIUDICE: qui")
    print("     guardo se L4.1 PARLA, che e' la domanda sull'estrattore, e")
    print("     riporto comunque l'esito.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
