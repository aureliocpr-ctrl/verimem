# -*- coding: utf-8 -*-
"""LA MAPPA DELLE SOGLIE — e la mia frase delle 20:43 che cade.

Alle 20:43 ho scritto al canale, del claim falso che il CE valuta 55.2:

    «55.2 sta sopra 40: quel falso conclamato passerebbe, se L4.1 non lo
     fermasse per via della cifra.»

E' SBAGLIATA, e questo banco la falsifica leggendo le soglie a runtime invece
di dedurle da una sola («threshold: 40.0») letta in una ricevuta.

Il prodotto ha soglie DIVERSE per giudici diversi, e in mezzo ha una banda:

  CE locale        cut 40   ma la banda [40, tau_hi) e' TRATTENUTA se enforced
  giudice LLM      cut 70   e la rubrica dice «50 = ... a confabulation»
                            ⇒ un verdetto di confabulazione conclamata sta
                              SOTTO la soglia del giudice che lo emette.

⇒ un 55.2 del CE non «passerebbe»: cade nella banda e viene trattenuto anche
senza L4.1. Il prodotto e' difeso DUE volte, non una, e il mio post lo
raccontava difeso una sola.

Questo banco stampa la mappa e mette accanto a ogni fascia cosa succede, cosi'
che la prossima volta nessuno di noi deduca il comportamento da una soglia sola.

CONTROLLO CHE DEVE POTER FALLIRE: se `band_enforced` fosse False, la banda NON
tratterrebbe e la mia frase del 20:43 tornerebbe vera. Il banco lo verifica e lo
dice, invece di assumerlo.

    python docs/stato-reale/banchi/la-mappa-delle-soglie-di-ammissione.py
"""

from __future__ import annotations

import sys


def main() -> int:
    from verimem.grounding_gate import (  # noqa: PLC0415
        LOCAL_CE_MOAT_THRESHOLD,
        _ce_band_enforced,
        _ce_band_tau_hi,
        resolve_write_threshold_for,
    )

    tau_hi = _ce_band_tau_hi()
    enforced = _ce_band_enforced()
    cut_ce = resolve_write_threshold_for("local")

    print("  LE SOGLIE, lette a runtime")
    for g in ("local", "claude", "local-band", "claude-band", None):
        print(f"    resolve_write_threshold_for({g!r:<14}) = {resolve_write_threshold_for(g)}")
    print(f"    LOCAL_CE_MOAT_THRESHOLD = {LOCAL_CE_MOAT_THRESHOLD}")
    print(f"    tau_hi = {tau_hi}   band_enforced = {enforced}")

    print("\n  LA RUBRICA che il prodotto manda al giudice LLM dichiara la scala:")
    print("    100 = the source states or unambiguously entails the fact")
    print("     50 = related but does NOT establish it (a confabulation)")
    print("      0 = does not support it or contradicts it")
    cut_llm = resolve_write_threshold_for("claude")
    if cut_llm > 50:
        print(f"    ⇒ la soglia del giudice LLM e' {cut_llm}: un verdetto di")
        print("      confabulazione conclamata (50) sta SOTTO, e viene respinto.")
        print("      Scala dichiarata e soglia numerica sono allineate.")
    else:
        print(f"    ⇒ la soglia del giudice LLM e' {cut_llm}, cioe' <= 50: un verdetto")
        print("      che la rubrica STESSA chiama confabulazione verrebbe ammesso.")

    print("\n  COSA SUCCEDE A UN PUNTEGGIO DEL CE, per fascia")
    for lo, hi, eti in ((0, cut_ce, "sotto il cut"), (cut_ce, tau_hi, "nella banda"),
                        (tau_hi, 100, "sopra tau_hi")):
        if eti == "sotto il cut":
            esito = "respinto"
        elif eti == "nella banda":
            esito = "TRATTENUTO per revisione (escalation tentata)" if enforced else "AMMESSO (banda non applicata)"
        else:
            esito = "ammesso"
        print(f"    [{lo:>5} , {hi:>5})   {eti:<14} -> {esito}")

    print("\n  IL CONTROLLO: la mia frase del 20:43 regge o cade?")
    if enforced and cut_ce < 55.2 < tau_hi:
        print("    CADE. Un 55.2 e' nella banda e viene trattenuto anche senza L4.1.")
        print("    Avevo dedotto il comportamento da UNA soglia letta in una ricevuta,")
        print("    e la ricevuta ne mostrava una sola perche' era quella del suo giudice.")
    elif not enforced:
        print("    REGGE, ma solo perche' band_enforced e' False in questo ambiente:")
        print("    con la banda spenta un 55.2 sta sopra il cut e verrebbe ammesso.")
    else:
        print("    ne' l'uno ne' l'altro: guarda i numeri sopra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
