"""PERCHE' `DOMAIN-PRECISION` NON COPRE I VERBALI — classificatore o percorso?

L'ODG del direttore (22:16) mette la specifica `L1` come punto ② e lascia
**due ipotesi aperte**, testuali: *«domain-precision e' ON di default dal 22/07
eppure NON copre i verbali LANT — capire perche' (**classificatore soggetto?
percorso?**) e' una via della cura»*.

⇒ **Questo banco le distingue**, ed e' l'unica cosa che fa.

  · `ENGRAM_L1_DOMAIN_PRECISION` sopprime l'escalation di `L1` **per fatto**,
    ma solo per le proposizioni che **il classificatore del soggetto** legge
    come *third-party professional fact* (`anti_confab_gate.py:2874-2875`).
  · Se il classificatore dice **False** sui verbali → **la causa e' il
    CLASSIFICATORE**, e la cura sta li'.
  · Se dice **True** e il verbale viene fermato lo stesso → **la causa e' il
    PERCORSO**: la condizione e' vera ma non arriva a spegnere l'escalation.

⚠️ **DUE PUNTI DEL CODICE SI CONTRADDICONO, e lo verifico invece di crederci**:
la funzione a `:184` dichiara **«DEFAULT ON** (flipped 2026-07-22)», il commento
a `:2866` dice **«DEFAULT OFF»**. Il banco **chiede al prodotto** quale sia vero.

CONTROLLI CHE POSSONO FALLIRE:
 (1) **controllo positivo del classificatore**: un self-claim palese («*la
     migrazione e' completata*») DEVE dare **False**. Se desse True, il
     classificatore direbbe sempre di si' e nessun conteggio varrebbe.
 (2) l'interruttore va **letto dal prodotto**, non assunto: se risulta OFF, il
     resto del banco misura una funzione spenta e lo dico.
 (3) i verbali sono **costruiti da me** e lo dichiaro: sono la forma dei casi
     `LANT`, non i casi originali, che non ho.

    python -u docs/stato-reale/banchi/perche-domain-precision-non-copre-i-verbali.py
"""

from __future__ import annotations

import sys

VERBALI = [
    "La pratica numero 2214 e' stata verificata dall'ufficio tecnico.",
    "Il collaudo dell'impianto e' stato completato dalla commissione il 12 marzo.",
    "La perizia e' stata conclusa dal geometra incaricato.",
    "L'istruttoria e' stata chiusa dal responsabile del procedimento.",
    "Il verbale di consegna e' stato firmato dal direttore dei lavori.",
    "La fornitura e' stata consegnata al magazzino di Verona.",
    "Il ciclo di terapia del paziente e' stato concluso dal reparto.",
    "La spedizione e' stata evasa dal centro logistico.",
]
SELF_CLAIM = [
    "La migrazione e' completata e tutti i test passano.",
    "Ho finito il refactoring e la suite e' verde.",
    "The migration is complete and all tests pass.",
    "Il cleanup del branch e' chiuso.",
]


def main() -> int:
    try:
        from verimem.anti_confab_gate import (
            _is_domain_professional_fact,
            _l1_domain_precision,
            run_validation_gate,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print("  -- CONTROLLO (2): l'interruttore, CHIESTO al prodotto")
    acceso = _l1_domain_precision()
    print(f"     _l1_domain_precision() = {acceso}")
    print("     (`:184` dichiara DEFAULT ON dal 22/07 · il commento a `:2866`"
          " dice DEFAULT OFF: uno dei due e' stantio)")
    if not acceso:
        print("     ⚠️ RISULTA SPENTO: il resto misura una funzione disattivata,")
        print("     e il commento a :2866 sarebbe quello giusto. Lo dico e vado")
        print("     avanti, perche' il classificatore si misura comunque.")

    print("\n  -- CONTROLLO (1): il classificatore dice NO ai self-claim?")
    sc = [(p, _is_domain_professional_fact(p)) for p in SELF_CLAIM]
    sbagliati = [p for p, v in sc if v]
    for p, v in sc:
        print(f"     {'DOMAIN' if v else 'non-dom':<8} {p[:62]}")
    if sbagliati:
        print(f"     CADUTO - {len(sbagliati)} self-claim letti come DOMAIN: il")
        print("     classificatore direbbe si' a tutto e il conteggio non vale.")
        return 1
    print(f"     retto - {len(SELF_CLAIM)} su {len(SELF_CLAIM)} letti come non-domain")

    print("\n  == I VERBALI: il classificatore li riconosce?")
    ris = [(p, _is_domain_professional_fact(p)) for p in VERBALI]
    dom = [p for p, v in ris if v]
    for p, v in ris:
        print(f"     {'DOMAIN' if v else '🔴 NON-dom':<11} {p[:60]}")
    print(f"\n     riconosciuti DOMAIN: {len(dom)} su {len(VERBALI)}"
          f"   ({100.0 * len(dom) / len(VERBALI):.0f}%)")

    print("\n  == E ALLA PORTA: il verbale entra o viene fermato?")
    print(f"     {'classif.':<10}{'esito':<11}{'layer':<28}claim")
    fermati_dom = 0
    for p, v in ris:
        g = run_validation_gate(proposition=p, verified_by=[], topic=None,
                                agent=None, source=None)
        az = str(getattr(g, "action", None))
        ws = getattr(g, "warnings", None) or []
        lay = ",".join(sorted({str((w or {}).get("layer") or "?")
                               for w in ws})) or "-"
        if v and az != "persist":
            fermati_dom += 1
        print(f"     {'DOMAIN' if v else 'non-dom':<10}{az:<11}{lay:<28}{p[:34]}")

    print("\n  == LA RISPOSTA ALLE DUE IPOTESI DELL'ODG")
    if not dom:
        print("     🔴 E' IL CLASSIFICATORE: nessuno degli otto verbali e' letto")
        print("     come third-party professional, quindi la carve-out non si")
        print("     attiva mai per loro. La cura sta nel classificatore, non nel")
        print("     percorso — e il percorso non e' nemmeno raggiunto.")
    elif fermati_dom:
        print(f"     🔴 E' IL PERCORSO: {len(dom)} verbali SONO letti come domain,")
        print(f"     eppure {fermati_dom} vengono fermati lo stesso. La condizione")
        print("     e' vera e non spegne l'escalation: il difetto sta a valle.")
    else:
        print(f"     🟢 NESSUNO DEI DUE: {len(dom)} verbali sono domain e passano.")
        print("     Su questa popolazione la carve-out FUNZIONA, e il caso LANT")
        print("     ha una terza causa che questo banco non tocca.")

    print("\n  ⚠️ COSA NON DICE: i verbali sono COSTRUITI da me — hanno la forma")
    print("  dei casi LANT, non sono quei casi. E il gate qui gira SENZA fonte:")
    print("  e' il regime dei self-claim, quello in cui `L1` e' progettato per")
    print("  scattare. Con una fonte il quadro puo' essere un altro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
