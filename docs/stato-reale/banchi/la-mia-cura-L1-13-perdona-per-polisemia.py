"""LA MIA CURA DI `L1.13` PERDONA PER POLISEMIA? — il buco che cerco nel mio lavoro.

`W7-60` ha misurato i verbali **senza fonte** e ha dichiarato il limite: *«con una
fonte il quadro puo' essere un altro, ed e' la misura successiva»*. Questa e'.

E c'e' un secondo motivo, piu' scomodo. La **cura che ho scritto io il 28/08**
(`_il_participio_e_nella_fonte`) perdona `L1.13` quando il participio che ha fatto
scattare il match **compare nella fonte**, e il criterio e' **testuale**:

    return matched_text.casefold() in source.casefold()

⇒ **Se la fonte contiene la stessa parola in un ALTRO SENSO, la mia cura perdona
lo stesso.** Un'altra istanza riporta il caso opposto (giudice 97,6 e `L1.13`
che ferma per polisemia, *«chiuso»* letto come *«task chiuso»*): **qui misuro il
verso in cui la polisemia fa PASSARE**, che e' quello di cui rispondo io.

LE TRE POPOLAZIONI, e la seconda e' il buco:
  **A. fonte che SOSTIENE** — il verbale e la sua fonte vera.
     atteso: **PASSA** (e' la cura che funziona).
  **B. fonte con lo STESSO PARTICIPIO in ALTRO SENSO** — *«l'istruttoria e' stata
     chiusa»* contro una fonte che dice *«il cantiere e' **chiuso** il lunedi'»*.
     atteso: **DEVE FERMARE** — la fonte non sostiene niente.
     🔴 **Se passa, la mia cura ha un buco**, ed e' un buco che ho aperto io.
  **C. fonte che NON contiene il participio** — atteso: **FERMA** (controllo).

CONTROLLI CHE POSSONO FALLIRE:
 (1) se **A** non passa, la cura non e' attiva in questa copia e il resto non
     significa niente: lo dico e mi fermo.
 (2) se **C** non ferma, `L1.13` e' spento e il banco non ha oggetto.
 (3) misuro **alla porta** (`run_validation_gate`), non solo il detector: il
     livello a cui misuri decide il verdetto.

    python -u docs/stato-reale/banchi/la-mia-cura-L1-13-perdona-per-polisemia.py
"""

from __future__ import annotations

import sys

CASI = [
    # (classe, claim, fonte, atteso)
    ("A sostiene",
     "L'istruttoria e' stata chiusa dal responsabile del procedimento.",
     "Verbale del 12 marzo: l'istruttoria relativa alla pratica 2214 e' stata "
     "chiusa dal responsabile del procedimento, che ne ha firmato il verbale.",
     "passa"),
    ("A sostiene",
     "Il collaudo dell'impianto e' stato completato dalla commissione.",
     "Verbale di collaudo: la commissione ha completato le verifiche "
     "sull'impianto e ha dichiarato il collaudo concluso senza rilievi.",
     "passa"),
    ("B POLISEMIA",
     "L'istruttoria e' stata chiusa dal responsabile del procedimento.",
     "Avviso al pubblico: il cantiere e' chiuso il lunedi' e nei giorni "
     "festivi. L'accesso e' consentito solo al personale autorizzato.",
     "ferma"),
    ("B POLISEMIA",
     "Il collaudo dell'impianto e' stato completato dalla commissione.",
     "Modulo di iscrizione: il campo va completato in stampatello. "
     "La domanda si presenta allo sportello entro il 30 aprile.",
     "ferma"),
    ("C assente",
     "L'istruttoria e' stata chiusa dal responsabile del procedimento.",
     "Ordine del giorno: si discute il bilancio e la nomina del revisore.",
     "ferma"),
]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim as det,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print(f"  {'classe':<14}{'atteso':<8}{'detector':<10}{'porta':<11}layer")
    esiti = []
    for classe, claim, fonte, atteso in CASI:
        d = det(proposition=claim, verified_by=None, source=fonte)
        g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                                agent=None, source=fonte)
        az = str(getattr(g, "action", None))
        ws = getattr(g, "warnings", None) or []
        lay = ",".join(sorted({str((w or {}).get("layer") or "?") for w in ws})) or "-"
        det_dice = "ferma" if d is not None else "passa"
        porta = "passa" if az == "persist" else "ferma"
        esiti.append((classe, atteso, det_dice, porta, lay))
        print(f"  {classe:<14}{atteso:<8}{det_dice:<10}{porta:<11}{lay}")

    A = [e for e in esiti if e[0].startswith("A")]
    B = [e for e in esiti if e[0].startswith("B")]
    C = [e for e in esiti if e[0].startswith("C")]

    print("\n  -- CONTROLLO (1): la mia cura del 28/08 e' ATTIVA? (classe A passa?)")
    a_ok = all(e[2] == "passa" for e in A)
    print(f"     detector su A: {[e[2] for e in A]}  ⇒ {'retto' if a_ok else 'CADUTO'}")
    if not a_ok:
        print("     La cura non perdona nemmeno la fonte che sostiene: in questa")
        print("     copia non e' attiva, e il resto del banco non significa nulla.")
        return 1

    print("\n  -- CONTROLLO (2): `L1.13` e' acceso? (classe C ferma?)")
    c_ok = all(e[2] == "ferma" for e in C)
    print(f"     detector su C: {[e[2] for e in C]}  ⇒ {'retto' if c_ok else 'CADUTO'}")
    if not c_ok:
        print("     Con una fonte che non porta il participio il detector tace:")
        print("     e' spento, e il banco non ha oggetto.")
        return 1

    print("\n  == LA RISPOSTA: la POLISEMIA (classe B)")
    b_passa = [e for e in B if e[2] == "passa"]
    print(f"     detector su B: {[e[2] for e in B]}")
    if b_passa:
        print(f"     🔴 LA MIA CURA HA UN BUCO: {len(b_passa)} casi su {len(B)}")
        print("     PASSANO. La fonte contiene la stessa parola in un ALTRO")
        print("     SENSO — «il cantiere e' chiuso il lunedi'» non dice niente")
        print("     sull'istruttoria — e il criterio testuale che ho scritto io")
        print("     (`matched_text in source`) non distingue i due sensi.")
        print("     ⇒ Ho scambiato «la parola c'e'» con «la fonte lo sostiene».")
    else:
        print("     🟢 REGGE: la polisemia non fa passare nulla. Il criterio")
        print("     testuale e' piu' stretto di quanto temessi, e il buco che")
        print("     cercavo nel mio lavoro non c'e' su questi casi.")

    # 🔬 IL CASO B CHE REGGE: regge per MERITO o per ACCIDENTE morfologico?
    #    Nel caso «chiusa» il claim dice `chiusa` e la fonte `chiuso`: il match
    #    testuale fallisce per la FLESSIONE, non perche' il criterio capisca il
    #    senso. Se e' cosi', con la stessa flessione deve passare — ed e' una
    #    predizione che puo' cadere.
    print("\n  == IL CASO CHE REGGE: merito o accidente morfologico?")
    PROVA = ("Il fascicolo e' stato chiuso dal responsabile.",
             "Avviso: la strada e' chiusa al traffico fino al 12 marzo. "
             "Il transito e' deviato sulla provinciale.")
    d2 = det(proposition=PROVA[0], verified_by=None, source=PROVA[1])
    print(f"     claim: {PROVA[0]}")
    print(f"     fonte: «la strada e' CHIUSA al traffico» (altro senso, stessa flessione? no)")
    print(f"     detector -> {'ferma' if d2 is not None else 'PASSA'}")
    PROVA2 = ("L'istruttoria e' stata chiusa dal responsabile.",
              "Avviso: la strada e' chiusa al traffico fino al 12 marzo.")
    d3 = det(proposition=PROVA2[0], verified_by=None, source=PROVA2[1])
    print(f"     claim: {PROVA2[0][:52]}")
    print("     fonte: «la strada e' CHIUSA al traffico» — STESSA flessione")
    print(f"     detector -> {'ferma' if d3 is not None else 'PASSA'}")
    if d3 is None:
        print("     🔑 PASSA ⇒ il caso B che reggeva reggeva per ACCIDENTE: la")
        print("     fonte diceva `chiuso` e il claim `chiusa`. Con la stessa")
        print("     flessione la mia cura perdona anche qui. ⇒ Cio' che la")
        print("     protegge NON e' il criterio, e' la morfologia italiana.")
    else:
        print("     ⇒ ferma anche con la stessa flessione: la mia spiegazione")
        print("     dell'accidente morfologico CADE, e il criterio regge per")
        print("     una ragione che non conosco.")

    print("\n  == E ALLA PORTA (livello che decide il verdetto)")
    for classe, atteso, det_dice, porta, lay in esiti:
        segno = "ok" if porta == atteso else "DIVERSO DALL'ATTESO"
        print(f"     {classe:<14}atteso {atteso:<7}porta {porta:<7}{segno}  [{lay}]")
    diff = [e for e in esiti if e[3] != e[2]]
    if diff:
        print(f"\n     🪞 {len(diff)} casi in cui DETECTOR e PORTA non coincidono:")
        print("     il layer dice una cosa e il sistema ne fa un'altra — sono")
        print("     due popolazioni, e vanno lette separate.")

    print("\n  ⚠️ COSA NON DICE: cinque casi, due verbi (`chiusa`, `completato`),")
    print("  fonti costruite da me. E misura il verso in cui la polisemia fa")
    print("  PASSARE: il verso opposto (ferma un vero) e' di chi l'ha riportato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
