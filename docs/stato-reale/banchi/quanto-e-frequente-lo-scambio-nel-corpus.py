"""PERCHE' NESSUN LAYER VEDE LO SCAMBIO DI ATTRIBUZIONE — la causa, nel codice.

Questo banco **nasce da un fallimento**, e il fallimento e' il risultato.

Volevo contare quanto pesa nel corpus la forma trovata in `W7-54` (un numero
VERO attribuito al soggetto SBAGLIATO, che entra con 99.5). Il candidato
naturale per contarla era `L4.2` — `valori_riusati_da_altro_contesto`, «il
numero c'e' ma riferito ad altro». **Il controllo positivo e' caduto subito:
`L4.2` non vede lo scambio.**

⇒ E leggendo il perche', il conteggio diventa una domanda meno interessante di
quella a cui il fallimento risponde. `vicinato_del_valore.py:147-148`:

    if claim_dopo & fonte_dopo:
        continue  # stessa grandezza: e' una riformulazione, il caso normale

🔑 **Nello scambio di attribuzione la GRANDEZZA COINCIDE PER COSTRUZIONE** —
inserzioni con inserzioni, euro con euro — **e cambia solo il SOGGETTO**. Quella
riga, che esiste per non gridare sulle riformulazioni legittime, **classifica
ogni scambio come legittimo**.

⚖️ **Non e' un bug: e' una scelta dichiarata nel commento.** Il difetto sta nella
SPECIFICA, non nell'implementazione — e per questo non si cura con una patch al
layer, si decide.

LE TRE MISURE, e la terza e' quella che rende la spiegazione falsificabile:
 (1) `L4.2` sullo SCAMBIO (stessa grandezza, soggetto diverso) -> atteso: TACE
 (2) `L4.2` sul RICALCO fedele -> atteso: TACE (e' il suo mestiere tacere qui)
 (3) 🔑 `L4.2` su un valore con GRANDEZZA DIVERSA -> **atteso: PARLA**.
     Se anche qui tacesse, la mia spiegazione sarebbe sbagliata e il layer
     sarebbe semplicemente spento. E' il controllo che puo' uccidere la tesi.

    python -u docs/stato-reale/banchi/quanto-e-frequente-lo-scambio-nel-corpus.py
"""

from __future__ import annotations

import sys

FONTE = (
    "Referto: il commit aaa ha aggiunto 86 inserzioni. "
    "Il commit bbb ha aggiunto 145 inserzioni. "
    "Il deposito di Prato ospita 300 bancali."
)
CASI = [
    ("SCAMBIO   (stessa grandezza, soggetto diverso)",
     "Il commit aaa ha aggiunto 145 inserzioni.", "tace"),
    ("RICALCO   (fedele)",
     "Il commit aaa ha aggiunto 86 inserzioni.", "tace"),
    ("GRANDEZZA DIVERSA (il caso per cui il layer esiste)",
     "Il magazzino ha ricevuto 300 pallet.", "parla"),
]


def main() -> int:
    try:
        from verimem.vicinato_del_valore import (
            _intorno,
            valori_riusati_da_altro_contesto,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print(f"  fonte fissata, {len(FONTE)} caratteri\n")
    print(f"  {'caso':<52}{'atteso':<8}{'osservato':<10}")
    esiti = {}
    for nome, claim, atteso in CASI:
        av = valori_riusati_da_altro_contesto(claim, FONTE)
        osservato = "parla" if av else "tace"
        esiti[nome] = (osservato == atteso, osservato, av)
        segno = "ok" if osservato == atteso else "SMENTITO"
        print(f"  {nome:<52}{atteso:<8}{osservato:<10}{segno}")

    print("\n  == PERCHE' TACE SULLO SCAMBIO — i due intorni, stampati")
    claim = CASI[0][1]
    for v in (145.0,):
        cd, cp = _intorno(claim, v)
        fd, fp = _intorno(FONTE, v)
        print(f"     valore {v:g}")
        print(f"       claim  dopo={sorted(cd)}  prima={sorted(cp)}")
        print(f"       fonte  dopo={sorted(fd)}  prima={sorted(fp)}")
        print(f"       dopo in comune  = {sorted(cd & fd)}   <- se NON vuoto, `continue`")
        print(f"       prima in comune = {sorted(cp & fp)}")

    ok_scambio = esiti[CASI[0][0]][0]
    ok_grandezza = esiti[CASI[2][0]][0]
    print("\n  -- IL CONTROLLO CHE PUO' UCCIDERE LA TESI (3)")
    if not ok_grandezza:
        print("     🪞 SMENTITA: il layer tace ANCHE sulla grandezza diversa, cioe'")
        print("     sul caso per cui esiste. Non e' «cieco allo scambio»: e' spento")
        print("     o lo sto chiamando male. LA MIA SPIEGAZIONE CADE.")
        return 1
    print("     retto - sulla grandezza diversa PARLA, quindi il layer e' acceso")
    print("     e il suo silenzio sullo scambio e' una DISTINZIONE, non un guasto.")

    print("\n  == LA CONCLUSIONE")
    if ok_scambio and ok_grandezza:
        print("     🔑 `L4.2` distingue: parla quando cambia la GRANDEZZA, tace")
        print("     quando cambia solo il SOGGETTO. ⇒ Lo scambio di attribuzione")
        print("     — numero giusto, soggetto sbagliato — **non ha nessun layer**")
        print("     che lo guardi, e per questo entra a 99.5 (W7-54).")
        print("     ⚖️ La riga che lo decide e' `vicinato_del_valore.py:147-148` e")
        print("     il suo commento la dichiara: «stessa grandezza: e' una")
        print("     riformulazione, il caso normale». **Scelta, non svista.**")
    print("\n  ⚠️ COSA NON DICE: NON conta quanto sia frequente la forma nel corpus")
    print("  — quello resta non misurato, e con questo rilevatore non e'")
    print("  misurabile. Dice PERCHE' non c'e' un rilevatore, che e' un'altra")
    print("  domanda e ha una risposta netta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
