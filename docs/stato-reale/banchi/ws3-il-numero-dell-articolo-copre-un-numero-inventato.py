# -*- coding: utf-8 -*-
"""Un numero INVENTATO passa se coincide col numero di un ARTICOLO della fonte?

Nasce da una misura di stasera su F1: `extract_quantities` legge «Art. 4 - La
penale ... al 5%» come `[('', 4.0), ('', 5.0)]` — il NUMERO DELL'ARTICOLO
finisce fra i valori, con unita' vuota, indistinguibile da una percentuale.

⇒ IPOTESI, e riguarda il PRODOTTO DI OGGI, non una cura futura: se i numeri
  d'articolo entrano nell'insieme dei valori della FONTE, allora un claim che
  inventa un numero UGUALE a un numero d'articolo risulta «presente nella
  fonte» e `L4.1` tace. Sarebbe un FALSO NEGATIVO in produzione.

A/B a variabile singola, stessa fonte, stesso claim, cambia SOLO la cifra:
    coperto     una cifra che coincide con un numero d'articolo (3..8)
    scoperto    una cifra che non coincide con niente (91, 97, ...)

LA PREDIZIONE, scritta prima di eseguire:
    scoperto -> quarantinato, L4.1 parla
    coperto  -> AMMESSO oppure L4.1 muto        <- il falso negativo

CONDIZIONE DI FALSIFICAZIONE: se anche i «coperti» sono quarantinati con L4.1
che parla, i numeri d'articolo NON coprono niente e l'ipotesi cade.

CONTROLLO CHE DEVE POTER FALLIRE: i claim VERI devono restare ammessi,
altrimenti sto misurando un gate rotto e non un buco.

REGIME: un processo, store temporaneo vuoto, porta SDK, validate='full', IT.
Strati letti da `warnings` (la ricevuta NON ha una chiave `layers`: cella 50).

    python docs/stato-reale/banchi/ws3-il-numero-dell-articolo-copre-un-numero-inventato.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)

# (etichetta, cifra, coincide con un numero d'articolo?)
CASI = [
    ("coperto  Art.3", "3", True),
    ("coperto  Art.6", "6", True),
    ("coperto  Art.8", "8", True),
    ("scoperto     91", "91", False),
    ("scoperto     97", "97", False),
    ("scoperto     43", "43", False),
]
MODELLO = "Il numero di rate previste dal contratto e' {}."

VERI = [
    "La penale per il ritardo e' pari al 2% dell'importo contrattuale.",
    "L'importo contrattuale e' di 148000 euro.",
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
    print("    store TEMPORANEO vuoto · un processo · porta SDK · validate='full' · IT")

    vf = sorted(extract_quantities(CONTRATTO, come_fonte=True))
    print(f"\n  [0] cosa il prodotto estrae dalla FONTE ({len(vf)} valori):")
    print(f"      {vf}")
    senza_unita = sorted(n for u, n in vf if u == "")
    print(f"      valori con unita' VUOTA: {senza_unita}")

    mem = Memory(str(Path(tempfile.mkdtemp()) / "art.db"))

    print("\n  [1] CONTROLLO: i claim VERI restano ammessi")
    for prop in VERI:
        r = mem.add(prop, topic=f"art/vero/{hash(prop) % 999}", source=CONTRATTO,
                    validate="full")
        st = str(r.get("status"))
        print(f"      {st:<12} ground={r.get('grounding_score')}  {prop[:48]}")
        if st == "quarantined":
            print("      CONTROLLO CADUTO: un VERO e' quarantinato ⇒ gate rotto,")
            print("      non un buco. NESSUN VERDETTO.")
            return 1

    print(f"\n  [2] {'caso':<16} {'esito':<13} {'ground':>7}  strati")
    print("      " + "-" * 62)
    righe = []
    for et, cifra, coperto in CASI:
        claim = MODELLO.format(cifra)
        r = mem.add(claim, topic=f"art/{cifra}", source=CONTRATTO, validate="full")
        st = str(r.get("status"))
        g = r.get("grounding_score")
        ls = _strati(r)
        parla41 = any("L4.1" in x for x in ls)
        righe.append((et, coperto, st != "quarantined", parla41,
                      float(g) if g is not None else -1.0))
        print(f"      {et:<16} {'AMMESSO' if st != 'quarantined' else 'quarantinato':<13} "
              f"{float(g or -1):7.1f}  {','.join(ls) if ls else '-'}")

    cop = [r for r in righe if r[1]]
    sco = [r for r in righe if not r[1]]
    print(f"\n  ══ LE DUE POPOLAZIONI ══")
    print(f"     COPERTI  (cifra = numero d'articolo)  ammessi {sum(1 for r in cop if r[2])}"
          f"/{len(cop)}   L4.1 parla su {sum(1 for r in cop if r[3])}/{len(cop)}")
    print(f"     SCOPERTI (cifra estranea)             ammessi {sum(1 for r in sco if r[2])}"
          f"/{len(sco)}   L4.1 parla su {sum(1 for r in sco if r[3])}/{len(sco)}")

    print("\n  ══ VERDETTO ══")
    l41_cop = sum(1 for r in cop if r[3])
    l41_sco = sum(1 for r in sco if r[3])
    if l41_sco > l41_cop:
        print("     IPOTESI RETTA: L4.1 parla sugli SCOPERTI e tace (o parla meno)")
        print("     sui COPERTI ⇒ il numero di un ARTICOLO copre un numero")
        print("     INVENTATO. E' un falso negativo del prodotto di OGGI, non una")
        print("     cura futura: la numerazione degli articoli entra fra i valori")
        print("     della fonte con unita' vuota.")
    elif l41_cop == l41_sco:
        print("     IPOTESI FALSIFICATA: L4.1 si comporta allo stesso modo sulle due")
        print("     popolazioni ⇒ i numeri d'articolo non coprono niente.")
    else:
        print("     RISULTATO INVERSO e da spiegare: L4.1 parla PIU' sui coperti.")
    print("\n  ⚠️ LIMITI: una fonte sola, sei casi, italiano, un solo modello di")
    print("     frase. Il verdetto finale di una scrittura dipende anche dal")
    print("     GIUDICE, non solo da L4.1: qui guardo se L4.1 PARLA, che e' la")
    print("     domanda sull'estrattore, e riporto anche l'esito complessivo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
