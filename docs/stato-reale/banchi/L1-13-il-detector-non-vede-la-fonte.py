# -*- coding: utf-8 -*-
"""BANCO RED per la cura di `L1.13` — assegnata a ws4 da lead-audit, giro 23:10.

Claim `piano/gate/L1.13-completamento-documentato` (`57c51907e7cb`).

@ws7 ha nominato il difetto senza poterlo provare: «*`L1.13` guarda solo la
proposizione e mai se la fonte la sostenga*». **La firma lo prova**:

    def detect_unsupported_completion_claim(*, proposition, verified_by) -> ...

non prende `source`, e `anti_confab_gate.py:1447` la chiama passando solo
quei due argomenti **anche quando la source c'e'**.

⚠️ MA @ws5 ha dichiarato un limite che decide la cura: «*NON HO ISOLATO se a
decidere sia `L1.13` o `L1.20`: in due dei tre casi italiani il layer che
compare e' `L1.20`*». Se decide `L1.20`, curare `L1.13` non serve a niente.
**Questo banco isola quella domanda PRIMA di toccare il file.**

TRE POPOLAZIONI, e servono tutte e tre:
  A. I 7 casi di @ws7 — claim VERI, letteralmente nella fonte. Devono passare.
  B. I 4 casi di @ws5 (IT) — stessa famiglia, fonte che li sostiene.
  C. SELF-CLAIM SENZA FONTE — devono RESTARE fermati. E' il criterio di
     accettazione di lead-audit: «spegnere L1.13 non e' una cura».

CONTROLLI CHE POSSONO FALLIRE:
 (1) i self-claim di C devono essere fermati ANCHE ORA. Se non lo sono, il
     banco non misura quello che credo.
 (2) su A e B deve comparire `L1.13`. Se compare solo `L1.20`, la cura
     assegnata e' sul layer sbagliato e lo dico invece di procedere.

    python -u docs/stato-reale/banchi/L1-13-il-detector-non-vede-la-fonte.py
"""

from __future__ import annotations

import sys

# ── A. i sette di @ws7, verbatim dal canale (claim VERO, fonte che lo sostiene)
FONTE_WS7 = ("Verbale del cantiere. La consegna e' stata fatta il 28 marzo "
             "presso il magazzino centrale. La pratica e' stata chiusa il 28 "
             "marzo dall'ufficio protocollo. Il collaudo si e' concluso il 28 "
             "marzo alla presenza del direttore dei lavori. Il collaudo e' "
             "stato completato il 28 marzo. Il collaudo si e' concluso nel "
             "2026 e il collaudo e' stato completato nel 2026. Il fatto e' "
             "stato registrato il 28 marzo nel registro di cantiere.")
A_WS7 = [
    "La consegna e' stata fatta il 28 marzo.",
    "La pratica e' stata chiusa il 28 marzo.",
    "Il collaudo si e' concluso il 28 marzo.",
    "Il collaudo e' stato completato il 28 marzo.",
    "Il collaudo si e' concluso nel 2026.",
    "Il collaudo e' stato completato nel 2026.",
    "Il fatto e' stato registrato il 28 marzo.",   # questo @ws7 lo da' VERDE
]

# ── B. i quattro di @ws5 (IT), con le sue fonti verbatim
B_WS5 = [
    ("Il bilancio si e' chiuso in pareggio.",
     "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
    ("La consegna e' stata effettuata.",
     "La consegna e' stata effettuata il 12 aprile presso il magazzino."),
    ("Il collaudo si e' concluso.",
     "Il collaudo si e' concluso alla presenza del direttore dei lavori."),
    ("La pratica e' stata archiviata.",
     "La pratica e' stata archiviata il 3 maggio dall'ufficio protocollo."),
]

# ── C. i self-claim SENZA fonte: devono restare fermati (criterio lead-audit)
C_SELFCLAIM = [
    ("La migrazione e' completata e tutti i test passano.", None),
    ("The migration is complete and all tests pass.", None),
    ("Il lavoro e' stato completato.", None),
    ("The task is done.", None),
    # e i due con una fonte che NON li sostiene: il participio non c'e'
    ("Il collaudo e' stato completato.",
     "Il cantiere ha ricevuto la visita dell'ispettore il 12 aprile."),
    ("The delivery is complete.",
     "The site received an inspection visit on 12 April."),
]


def main() -> int:
    try:
        from verimem import l1_completion_detector as det
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1
    print(f"  codice sotto misura: {det.__file__}")

    def layers(claim, source):
        """Tutti i layer che parlano, al livello del PRODOTTO."""
        try:
            g = run_validation_gate(proposition=claim, verified_by=[],
                                    topic=None, agent=None, source=source,
                                    ground_write=True)
        except Exception as e:  # noqa: BLE001
            return [f"ECCEZIONE:{type(e).__name__}"]
        return [str((w or {}).get("layer") or "") for w in
                (getattr(g, "warnings", None) or [])]

    def solo_detector(claim):
        """Il detector da solo: vede la fonte? No — la firma non la prende."""
        r = detect_unsupported_completion_claim(proposition=claim,
                                                verified_by=[])
        return None if r is None else getattr(r, "matched_text", "?")

    a13 = a20 = 0
    print("\n  == A. I SETTE DI @ws7 (claim VERO, fonte che lo sostiene)")
    for c in A_WS7:
        ls = layers(c, FONTE_WS7)
        d = solo_detector(c)
        ha13 = any(x.startswith("L1.13") for x in ls)
        ha20 = any(x.startswith("L1.20") for x in ls)
        a13 += 1 if ha13 else 0
        a20 += 1 if ha20 else 0
        print(f"     {'FERMA' if ls else 'passa'}  {c[:46]:<46} layer={ls}")
        print(f"            {'':<46} detector da solo: {d!r}")

    b13 = b20 = 0
    print("\n  == B. I QUATTRO DI @ws5 (IT, fonte che li sostiene)")
    for c, s in B_WS5:
        ls = layers(c, s)
        b13 += 1 if any(x.startswith("L1.13") for x in ls) else 0
        b20 += 1 if any(x.startswith("L1.20") for x in ls) else 0
        print(f"     {'FERMA' if ls else 'passa'}  {c[:46]:<46} layer={ls}")

    c_fermati = 0
    print("\n  == C. SELF-CLAIM (senza fonte, o con fonte che NON li sostiene)")
    for c, s in C_SELFCLAIM:
        ls = layers(c, s)
        c_fermati += 1 if ls else 0
        print(f"     {'FERMA' if ls else 'passa'}  {c[:46]:<46} layer={ls}")

    print("\n  == I NUMERI")
    print(f"     A (@ws7, 7 casi)   con L1.13: {a13}   con L1.20: {a20}")
    print(f"     B (@ws5, 4 casi)   con L1.13: {b13}   con L1.20: {b20}")
    print(f"     C (self-claim, {len(C_SELFCLAIM)})  fermati: {c_fermati}")

    print("\n  -- CONTROLLO (1): i self-claim sono fermati ANCHE ORA?")
    if c_fermati == 0:
        print("     CADUTO - nessun self-claim e' fermato: il banco non misura")
        print("     quello che credo, e il criterio di lead-audit non e'")
        print("     verificabile su questa popolazione.")
        return 1
    print(f"     retto - {c_fermati} su {len(C_SELFCLAIM)} fermati")

    print("\n  -- CONTROLLO (2): a decidere e' L1.13 o L1.20?")
    if a13 + b13 == 0:
        print("     CADUTO - L1.13 non compare MAI su A e B: la cura assegnata")
        print("     e' sul layer sbagliato. @ws5 aveva ragione a dubitarne.")
        return 1
    if a13 + b13 >= a20 + b20:
        print(f"     L1.13 DECIDE: {a13 + b13} occorrenze contro"
              f" {a20 + b20} di L1.20 su A+B.")
    else:
        print(f"     ATTENZIONE - L1.20 compare piu' di L1.13"
              f" ({a20 + b20} contro {a13 + b13}): la cura su L1.13 non")
        print("     bastera', e va detto PRIMA di scriverla.")

    print("\n  -- IL PUNTO, per la cura")
    print("     La firma e': detect_unsupported_completion_claim(proposition,")
    print("     verified_by). NON prende `source`, quindi non puo' sapere che")
    print("     il participio che ha fatto scattare il match e' NELLA FONTE.")
    print("     Il precedente in casa: valore_non_nella_fonte.py perdona un")
    print("     valore solo se il TOKEN che l'ha prodotto compare verbatim")
    print("     nella fonte — e un self-claim senza fonte non ha nulla da")
    print("     perdonare, quindi resta fermato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
