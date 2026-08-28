"""DOVE STA LA SOGLIA, e SERVE che il testo aggiunto porti NUMERI?

W7-40 ha misurato che **+54 caratteri** su una fonte di 453 portano uno scambio
di attribuzione da `72.1` a oltre `99`, e che **sei contenuti diversi fanno la
stessa cosa** ⇒ decide la quantita', non il contenuto.

⚠️ MA TUTTI E SEI QUEGLI ARTICOLI PORTAVANO NUMERI (34%, 61%, 16 euro, 50 euro,
8 giorni, 45 giorni). ⇒ «Non e' il contenuto» era corretto **fra quei sei**, e
lascia aperta una distinzione che il banco non poteva fare: **serve la lunghezza,
o serve che il testo aggiunto porti altri NUMERI?**

Qui la separo, e cerco il punto esatto:
  ① NEUTRO SENZA NUMERI — prosa contrattuale generica, zero cifre
  ② NEUTRO CON NUMERI   — la stessa prosa con qualche cifra dentro
a passi di ~6 caratteri, e su TRE claim insieme.

TRE POPOLAZIONI, e la terza e' quella che rende leggibile il numero:
  · SCAMBIO      deve ribaltarsi (e' il fenomeno)
  · VERO         deve restare ammesso (se si muove anche lui, non e' lo scambio)
  · CIFRA ASSENTE deve restare fermata a OGNI lunghezza — il dossier ⑬ dice
    «*fermata a ogni lunghezza, mai una fuga*». **Se cede anche lei, allora non
    e' una soglia dello scambio: e' il giudice che molla**, e sarebbe il
    risultato piu' grave della serata.

CONTROLLI CHE POSSONO FALLIRE:
 (1) a delta 0 lo SCAMBIO dev'essere fermato: se entra gia' sulla nuda, il
     fenomeno non c'e' e il resto non significa niente.
 (2) la CIFRA ASSENTE dev'essere fermata a delta 0: se non lo e', il mio
     controllo negativo non e' negativo.

    python -u docs/stato-reale/banchi/dove-sta-la-soglia-e-serve-che-il-testo-porti-numeri.py
"""

from __future__ import annotations

import sys

NUDA = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)

# ① prosa contrattuale SENZA una sola cifra
SENZA_NUMERI = (" Le parti dichiarano di aver letto e compreso ogni clausola del "
                "presente accordo e di accettarne integralmente il contenuto, "
                "riservandosi ogni facolta' di legge in ordine alle obbligazioni "
                "reciproche qui assunte nonche' alle modalita' esecutive convenute.")
# ② la stessa cosa, ma con cifre dentro
CON_NUMERI = (" Le parti dichiarano ai sensi 4 di aver letto 9 ogni clausola 3 del "
              "presente accordo 7 e di accettarne 5 il contenuto 8, riservandosi "
              "ogni facolta' 6 di legge 2 in ordine alle obbligazioni 4 reciproche "
              "qui assunte 9 nonche' alle modalita' 3 esecutive convenute 7.")

CLAIM = [
    ("SCAMBIO", "La cauzione definitiva e' pari a 148000 euro."),
    ("VERO", "L'importo contrattuale e' di 148000 euro."),
    ("ASSENTE", "La cauzione definitiva e' pari a 99999 euro."),
]
PASSI = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 80, 120, 180]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    def giudica(claim, fonte):
        g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                                agent=None, source=fonte, ground_write=True)
        return (getattr(g, "grounding_score", None) or 0.0,
                getattr(g, "action", None))

    print("  -- CONTROLLI (1) e (2): la base e' quella attesa?")
    s0 = giudica(CLAIM[0][1], NUDA)
    a0 = giudica(CLAIM[2][1], NUDA)
    print(f"     SCAMBIO su NUDA : {s0[1]}  score={s0[0]:.1f}")
    print(f"     ASSENTE su NUDA : {a0[1]}  score={a0[0]:.1f}")
    if s0[1] == "persist":
        print("     CADUTO - lo scambio entra gia' sulla nuda: niente fenomeno.")
        return 1
    if a0[1] == "persist":
        print("     CADUTO - la cifra assente entra gia' sulla nuda: il mio")
        print("     controllo negativo non e' negativo.")
        return 1
    print("     retto - entrambi fermati sulla fonte nuda")

    for nome_coda, coda in (("① SENZA NUMERI", SENZA_NUMERI),
                            ("② CON NUMERI", CON_NUMERI)):
        print(f"\n  == {nome_coda}  (coda di {len(coda)} char)")
        print(f"     {'delta':>6} {'tot':>5}  "
              f"{'SCAMBIO':<18}{'VERO':<18}{'ASSENTE'}")
        primo_ribalto = None
        for d in PASSI:
            if d > len(coda):
                break
            fonte = NUDA + coda[:d]
            riga = []
            for _n, c in CLAIM:
                sc, ac = giudica(c, fonte)
                riga.append(f"{ac[:7]:<8}{sc:>7.1f}  ")
            sc_sc, ac_sc = giudica(CLAIM[0][1], fonte)
            if primo_ribalto is None and ac_sc == "persist":
                primo_ribalto = d
            print(f"     {d:>6} {len(fonte):>5}  {''.join(riga)}")
        if primo_ribalto is None:
            print(f"     ⇒ lo scambio NON si ribalta con {nome_coda}")
        else:
            print(f"     ⇒ lo scambio si ribalta a delta = +{primo_ribalto}"
                  f" caratteri")

    print("\n  == COSA GUARDARE nelle colonne")
    print("     · se VERO resta `persist` ovunque: la soglia riguarda lo scambio")
    print("     · se ASSENTE resta `downgrad` ovunque: il giudice NON molla, e")
    print("       il fenomeno e' specifico dello scambio di attribuzione")
    print("     · se ASSENTE cede a un certo delta: NON e' una soglia dello")
    print("       scambio, e' il giudice — ed e' il risultato piu' grave")
    print("     · se ① NON ribalta e ② si': non e' la lunghezza, servono NUMERI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
