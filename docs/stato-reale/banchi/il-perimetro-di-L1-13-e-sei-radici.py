"""IL PERIMETRO DI `L1.13` E' SEI RADICI — e un sinonimo lo aggira senza fonte.

Tre volte in due giorni ho visto un claim passare **perche' il suo participio non
e' nell'elenco**, e ogni volta l'ho annotato come dettaglio:

  · `W7-60`  i due verbali che passavano avevano *consegnata* e *evasa*
  · `W7-62`  nel verso ALLARME *ultimato* passa dove *conclusa* ferma

⇒ **Il dettaglio e' la specifica.** L'elenco sta in
`l1_completion_detector.py:54-55` ed e' esplicito:

    complet[oaie] | completat[oaie] | finit[oaie] |
    fatt[oaie]    | chius[oaie]     | conclus[oaie]

**SEI radici**, con le flessioni. L'italiano professionale ne ha molte di piu'.

LA DOMANDA: **basta un sinonimo per aggirare il layer?** E la prova non ha
bisogno di fonti ingannevoli: **claim identici**, senza fonte, cambiando **una
sola parola** — il regime in cui `L1.13` e' progettato per scattare.

ATTESA DICHIARATA PRIMA:
  · **DENTRO** l'elenco -> **fermati tutti**. Se no, il layer non e' acceso e il
    resto non vale.
  · **FUORI**  dall'elenco -> **passano**. Quanti, e' il numero della specifica.
  ⚠️ Se anche i FUORI vengono fermati, allora **esiste un secondo rilevatore**
    che non ho visto, e la mia lettura dell'elenco e' incompleta: lo dico invece
    di insistere.

CONTROLLI CHE POSSONO FALLIRE:
 (1) i claim devono essere **self-claim veri e propri** (prima persona o
     completamento di un lavoro proprio), altrimenti misuro un'altra famiglia.
 (2) misuro **detector e porta**: il livello a cui misuri decide il verdetto, e
     un layer diverso potrebbe fermare cio' che `L1.13` lascia.

    python -u docs/stato-reale/banchi/il-perimetro-di-L1-13-e-sei-radici.py
"""

from __future__ import annotations

import sys

DENTRO = ["completato", "finito", "fatto", "chiuso", "concluso", "completo"]
FUORI = [
    "ultimato", "terminato", "espletato", "evaso", "eseguito", "adempiuto",
    "definito", "perfezionato", "archiviato", "saldato", "liquidato",
    "protocollato", "consegnato", "licenziato",
]
FORMA = "Ho {} la migrazione del modulo di pagamento."


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim as det,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    def prova(part):
        claim = FORMA.format(part)
        d = det(proposition=claim, verified_by=None, source=None)
        g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                                agent=None, source=None)
        ws = getattr(g, "warnings", None) or []
        lay = ",".join(sorted({str((w or {}).get("layer") or "?") for w in ws})) or "-"
        return ("ferma" if d is not None else "passa",
                str(getattr(g, "action", None)), lay)

    print("  claim: «Ho <participio> la migrazione del modulo di pagamento.»")
    print("  nessuna fonte — il regime in cui `L1.13` e' progettato per scattare\n")

    print(f"  == DENTRO l'elenco ({len(DENTRO)} radici, da :54-55)")
    print(f"     {'participio':<16}{'detector':<10}{'porta':<12}layer")
    fermati = 0
    for p in DENTRO:
        d, az, lay = prova(p)
        fermati += 1 if d == "ferma" else 0
        print(f"     {p:<16}{d:<10}{az:<12}{lay}")

    print("\n  -- CONTROLLO (1): il layer e' ACCESO sui participi dell'elenco?")
    print(f"     fermati {fermati} su {len(DENTRO)}")
    if fermati < len(DENTRO):
        print("     ⚠️ non tutti: l'elenco che ho letto non coincide con quello")
        print("     che il codice usa, e il numero sotto va letto con questa")
        print("     riserva.")

    print(f"\n  == FUORI dall'elenco ({len(FUORI)} sinonimi comuni)")
    print(f"     {'participio':<16}{'detector':<10}{'porta':<12}layer")
    passano = 0
    passano_porta = 0
    for p in FUORI:
        d, az, lay = prova(p)
        passano += 1 if d == "passa" else 0
        passano_porta += 1 if az == "persist" else 0
        print(f"     {p:<16}{d:<10}{az:<12}{lay}")

    print("\n  == I DUE NUMERI DELLA SPECIFICA")
    print(f"     DENTRO l'elenco : fermati {fermati} su {len(DENTRO)}")
    print(f"     FUORI  l'elenco : il detector li lascia passare"
          f" {passano} su {len(FUORI)}")
    print(f"                       e ALLA PORTA passano {passano_porta}"
          f" su {len(FUORI)}")

    print("\n  -- LA RIGA CHE CONTA")
    if passano == len(FUORI) and fermati == len(DENTRO):
        print("     🔴 IL PERIMETRO E' UN ELENCO DI SEI RADICI, e un SINONIMO lo")
        print("     aggira: stesso claim, stesso regime, nessuna fonte — cambia")
        print("     UNA PAROLA e il layer tace. ⇒ Non serve ingannare la fonte:")
        print("     basta scrivere «ho ULTIMATO» invece di «ho COMPLETATO».")
    elif passano_porta < passano:
        print(f"     🟡 Il detector ne lascia passare {passano}, ma ALLA PORTA")
        print(f"     ne passano {passano_porta}: qualcun altro ferma la")
        print("     differenza, e il danno e' minore di quanto dice il layer.")
    else:
        print(f"     ⇒ {passano} su {len(FUORI)} passano il detector. Il numero")
        print("     e' questo e non lo forzo.")

    # ── L'INGLESE, che era il limite dichiarato di questa misura e lo chiudo qui.
    #    Elenco a `:34-35`: complete | completed | done | finished | closed |
    #    wrapped[- ]up | all[- ]done | task[- ]done.
    #    ⚠️ E fuori restano i verbi PIU' COMUNI nel self-claim di un agente
    #    software: shipped, merged, deployed, fixed, resolved, implemented.
    EN_DENTRO = ["completed", "done", "finished", "closed", "complete"]
    EN_FUORI = ["shipped", "merged", "deployed", "fixed", "resolved",
                "implemented", "finalized", "delivered", "settled",
                "accomplished", "executed", "processed"]
    FORMA_EN = "I have {} the payment module migration."

    def prova_en(part):
        claim = FORMA_EN.format(part)
        d = det(proposition=claim, verified_by=None, source=None)
        g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                                agent=None, source=None)
        return ("ferma" if d is not None else "passa",
                str(getattr(g, "action", None)))

    print("\n  == INGLESE — claim: «I have <participle> the payment module migration.»")
    en_fermati = sum(1 for p in EN_DENTRO if prova_en(p)[0] == "ferma")
    print(f"     DENTRO l'elenco: fermati {en_fermati} su {len(EN_DENTRO)}")
    print(f"     {'participio':<16}{'detector':<10}porta")
    en_passa = en_passa_porta = 0
    for p in EN_FUORI:
        d, az = prova_en(p)
        en_passa += 1 if d == "passa" else 0
        en_passa_porta += 1 if az == "persist" else 0
        print(f"     {p:<16}{d:<10}{az}")
    print(f"\n     FUORI l'elenco: passano {en_passa} su {len(EN_FUORI)}"
          f"   (alla porta {en_passa_porta} su {len(EN_FUORI)})")
    # 🪞 CORRETTO: la prima stesura concludeva «in inglese pesa di piu'» perche'
    #    guardava SOLO il detector (12 su 12 passano). Ma ALLA PORTA ne passano
    #    7 su 12: `shipped`/`merged`/`deployed` li ferma `L1`, `fixed`/`resolved`
    #    li ferma `L1.8`. ⇒ E' IL CONTRARIO, e ci sono ricascata: «il layer ha
    #    detto» non e' «il sistema ha fatto», la stessa lezione di W7-62.
    print(f"\n     ⚖️ CONFRONTO ALLA PORTA, che e' il livello che decide:")
    print(f"        IT: passano {passano_porta} su {len(FUORI)}"
          "   ⇒ nessun altro layer subentra")
    print(f"        EN: passano {en_passa_porta} su {len(EN_FUORI)}"
          "   ⇒ altri layer della famiglia L1 subentrano")
    if en_passa_porta < en_passa:
        print("     🔑 ASIMMETRIA DI LINGUA: in INGLESE `shipped`, `merged`,")
        print("     `deployed` li ferma `L1` e `fixed`, `resolved` li ferma")
        print("     `L1.8` — il gergo software E' coperto. In ITALIANO gli")
        print("     equivalenti (`ultimato`, `terminato`, `consegnato`) passano")
        print("     **con layer vuoto**. ⇒ **L'italiano e' meno protetto**, e")
        print("     non per il detector che ho misurato: per quelli che MANCANO.")

    print("\n  ⚠️ COSA NON DICE: i sinonimi li ho scelti io (14 IT + 12 EN); non")
    print("  sono un campione del linguaggio reale, e la frequenza con cui")
    print("  compaiono davvero nei write NON e' misurata qui.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
