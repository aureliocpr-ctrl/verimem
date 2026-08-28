# -*- coding: utf-8 -*-
"""FIRMA ESTERNA SUL CODICE: `L4.3` contro la MIA popolazione, non la sua.

Alle 20:24 ho firmato il design F1 e ho scritto il limite: «ho verificato la
baseline, non il meccanismo — `L4.3` non esiste ancora come codice, quindi
nessuno puo' firmarne il comportamento». Alle 20:37 @ws3 ha scritto
`verimem/soggetto_valore.py`. ⇒ il limite e' cadutо: ora il comportamento si
misura.

Lo misuro con la MIA popolazione — i dodici scambi del banco
`lo-scambio-e-simmetrico-o-no.py`, sei coppie in entrambi i versi, piu' i claim
VERI di controllo. Sono i casi che ho costruito io prima che il design
esistesse, quindi non sono stati scelti per farlo passare: e' esattamente la
condizione che il design doc chiede («*il banco lo scriva chi non ha in mente la
cura*»).

La predizione del design, verbatim: **SCAMBIO ≤ 3/12 (segnalati ≥ 7 dei 10)**, e
**≤ 1 nuovo falso positivo**; qualunque regressione sui veri e' bloccante.

Qui si misura `avviso_soggetto_valore(proposition, source)` da sola — non il
gate: il layer non e' ancora agganciato (`git grep soggetto_valore` in
`verimem/*.py` trova solo se stesso), quindi questo NON dice cosa farebbe il
prodotto, dice cosa fa la funzione.

CONTROLLI CHE DEVONO POTER FALLIRE: i claim VERI non devono essere segnalati
(ogni segnalazione su un vero e' un falso positivo, e la predizione ne concede
al massimo uno); e la funzione dev'essere importabile — se non lo e', il banco
lo dice invece di misurare il vuoto.

    python docs/stato-reale/banchi/L4-3-contro-la-mia-popolazione.py
"""

from __future__ import annotations

import sys

FONTE = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)

SCAMBI = [
    "La penale per il ritardo e' pari al 7% dell'importo contrattuale.",
    "La penale per difformita' qualitativa e' pari al 2% dell'importo contrattuale.",
    "Il termine di consegna e' fissato al 30 aprile 2027.",
    "Il termine per la contestazione dei vizi e' fissato al 12 marzo 2027.",
    "La cauzione definitiva e' pari a 148000 euro.",
    "L'importo contrattuale e' di 22000 euro.",
]
VERI = [
    "La penale per il ritardo e' pari al 2% dell'importo contrattuale.",
    "La penale per difformita' qualitativa e' pari al 7% dell'importo contrattuale.",
    "Il termine di consegna e' fissato al 12 marzo 2027.",
    "Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027.",
    "L'importo contrattuale e' di 148000 euro.",
    "La cauzione definitiva e' pari a 22000 euro.",
]
# cifra ASSENTE: il mio controllo negativo — L4.3 non deve toccarla (e' di L4.1)
ASSENTI = [
    "La cauzione definitiva e' pari a 99999 euro.",
    "L'importo contrattuale e' di 91234 euro.",
]


def main() -> int:
    try:
        from verimem import soggetto_valore as sv
        from verimem.soggetto_valore import avviso_soggetto_valore
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito — {type(e).__name__}: {e}")
        return 1
    print(f"  codice sotto misura: {sv.__file__}")

    def prova(gruppo: str, claims: list[str]) -> tuple[int, list[str]]:
        segnalati, dettagli = 0, []
        for c in claims:
            try:
                r = avviso_soggetto_valore(c, FONTE)
            except Exception as e:  # noqa: BLE001
                dettagli.append(f"    ECCEZIONE {type(e).__name__}: {c[:48]}")
                continue
            if r:
                segnalati += 1
                nota = str(r.get("reason") or r.get("motivo") or r)[:56]
                dettagli.append(f"    SEGNALA  {c[:52]}  → {nota}")
            else:
                dettagli.append(f"    tace     {c[:52]}")
        return segnalati, dettagli

    print(f"\n  ══ SCAMBI (la famiglia che il layer deve cogliere) — {len(SCAMBI)} casi")
    n_sc, det = prova("scambi", SCAMBI)
    for d in det:
        print(d)
    print(f"    ⇒ segnalati {n_sc} su {len(SCAMBI)}")

    print(f"\n  ══ VERI (nessuno deve essere segnalato) — {len(VERI)} casi")
    n_v, det = prova("veri", VERI)
    for d in det:
        print(d)
    print(f"    ⇒ falsi positivi {n_v} su {len(VERI)}")

    print(f"\n  ══ CIFRA ASSENTE (non e' affare di L4.3, il passo 1 la lascia a L4.1)")
    n_a, det = prova("assenti", ASSENTI)
    for d in det:
        print(d)
    print(f"    ⇒ toccati {n_a} su {len(ASSENTI)}")

    print("\n  -- CONTROLLO: nessun falso positivo sui VERI")
    if n_v > 1:
        print(f"     CADUTO — {n_v} falsi positivi, e la predizione ne concede al massimo 1.")
        print("     Sulla MIA popolazione il design non regge come scritto.")
        return 1
    print(f"     retto — {n_v} falso positivo (la predizione ne concede 1)")

    print("\n  -- LA PREDIZIONE, sulla mia popolazione")
    print(f"     scambi segnalati: {n_sc}/{len(SCAMBI)} · falsi positivi: {n_v}/{len(VERI)}"
          f" · cifra assente toccata: {n_a}/{len(ASSENTI)}")
    if n_sc >= 4 and n_v <= 1 and n_a == 0:
        print("     ⇒ REGGE su questa popolazione: coglie la maggioranza degli scambi,")
        print("       non tocca i veri e lascia la cifra assente a L4.1 come promesso.")
    elif n_sc == 0:
        print("     ⇒ NON COGLIE NIENTE sulla mia popolazione: il meccanismo non")
        print("       riconosce gli scambi che ho costruito io.")
    else:
        print("     ⇒ parziale: guarda le righe sopra prima di citare un numero.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
