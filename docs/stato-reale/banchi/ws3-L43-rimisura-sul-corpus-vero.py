"""`L4.3` sul CORPUS VERO — la rimisura prima di collegarlo al gate.

Vincolo di @lead-audit per il via libera: «*rimisura finale sul banco
corpus-vero `3f961371` prima di dichiarare la cura*». Questa è quella misura,
fatta **prima** di collegare il layer al gate: se il tasso di falsi allarmi
fosse alto, collegarlo sarebbe sbagliato — **misurare viene prima di curare**.

LA POPOLAZIONE, e non l'ho scelta io: i fatti che il prodotto ha **già
ammesso** con `grounding_score >= 90`, col `grounding_span` che ha **davvero**
usato per giudicarli. È la popolazione di @ws5 (banco `3f961371`), ripresa
perché il confronto valga: lei ha misurato la regola **trascritta**, io misuro
il **codice**.

    sola lettura (`mode=ro`) · percorso chiesto a `CONFIG.semantic_db`
    NESSUNA scrittura sullo store di Aurelio

IL NUMERO DI RIFERIMENTO, dal suo banco: sui giudicabili, la regola **senza le
guardie** segnalava il **65,7%**; **con le tre guardie** il **5,3%**. Qui il
codice le ha dentro dal primo commit, quindi la previsione è:

    PREDIZIONE, scritta prima di eseguire: la quota di segnalati sui
    giudicabili sta SOTTO il 10%. Sopra il 20% il layer non va collegato.

⚠️ E il limite che @ws5 ha dichiarato e che vale anche qui: **«grounding alto»
non è «vero»**, è «*il giudice lo ha ritenuto sostenuto*». Se il giudice
sbaglia, un mio «falso allarme» è **una cattura giusta**. Il numero qui sotto
è una quota di **segnalati**, non di **errori**, e chiamarla altrimenti
sarebbe lo stesso sbaglio del 65,7% nudo.

    python docs/stato-reale/banchi/ws3-L43-rimisura-sul-corpus-vero.py
"""

from __future__ import annotations

import sqlite3
import sys


def main() -> int:
    from verimem.config import CONFIG
    from verimem.soggetto_valore import avviso_soggetto_valore

    db = str(CONFIG.semantic_db)
    print("  REGIME, dichiarato E misurato:")
    print(f"    store: {db}")
    print("    SOLA LETTURA (mode=ro) · nessuna scrittura · store di Aurelio")
    print("    layer: verimem/soggetto_valore.py (il CODICE, non una trascrizione)")

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        righe = list(con.execute(
            "SELECT proposition, grounding_span FROM facts "
            "WHERE grounding_span IS NOT NULL AND length(grounding_span) > 0 "
            "AND grounding_score >= 90"))
    finally:
        con.close()
    print(f"    fatti ammessi con span e grounding >= 90: {len(righe)}")

    segnalati = []
    esaminati = 0
    for prop, span in righe:
        if not prop or not span:
            continue
        esaminati += 1
        a = avviso_soggetto_valore(prop, span)
        if a is not None:
            segnalati.append((prop, span, a))

    if not esaminati:
        print("\n  CONTROLLO CADUTO: zero fatti esaminati ⇒ la query non seleziona")
        print("  niente. NESSUNA QUOTA.")
        return 1

    quota = 100.0 * len(segnalati) / esaminati
    print(f"\n  ══ IL NUMERO ══")
    print(f"     esaminati ......... {esaminati}")
    print(f"     SEGNALATI ......... {len(segnalati)}   ({quota:.1f}%)")
    print(f"     riferimento di @ws5: 65,7% senza guardie · 5,3% con le tre guardie")

    print("\n  I PRIMI SEGNALATI, per farsi un'idea (non sono un campione casuale):")
    for prop, _span, a in segnalati[:5]:
        print(f"     · claim : {prop[:88]}")
        print(f"       motivo: {a['reason'][:88]}")

    print("\n  ══ VERDETTO sulla PREDIZIONE ══")
    print(f"     previsto: SOTTO il 10%   ·   misurato: {quota:.1f}%")
    if quota < 10:
        print("     RETTA: le guardie tengono la quota bassa sul corpus vero.")
        print("     Il layer si puo' collegare come AVVISO.")
    elif quota < 20:
        print("     SBAGLIATA nella taglia: sopra il 10% ma sotto il 20%. Si puo'")
        print("     collegare come avviso, dichiarando la quota.")
    else:
        print("     FALSIFICATA: sopra il 20%. IL LAYER NON VA COLLEGATO cosi'.")

    print("\n  ⚠️ LIMITI: «grounding alto» non e' «vero», e' «il giudice lo ha")
    print("     ritenuto sostenuto» ⇒ questa e' una quota di SEGNALATI, non di")
    print("     ERRORI: se il giudice sbaglia, un segnalato e' una cattura giusta.")
    print("     Lo span e' TRONCATO a 400 caratteri dal prodotto. Il corpus e'")
    print("     fatto di OUTPUT DI STRUMENTI, non di contratti in prosa. E si")
    print("     muove mentre lo misuri: siamo otto a scrivere.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
