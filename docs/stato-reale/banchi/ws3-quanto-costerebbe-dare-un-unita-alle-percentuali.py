"""Quanto costerebbe dare un'unità alle PERCENTUALI? — misurato PRIMA di curare.

Difetto ① dell'estrattore, ancora aperto e misurato il 28/08::

    extract_quantities(«La penale ... e' pari al 2% ...», come_fonte=True)
        ->  [('', 2.0)]        <- la percentuale esce SENZA unita'

⇒ oggi «2%» e il «2» nudo di qualunque altra cosa sono **lo stesso valore**.
Curarlo — dare a `%` un'unità propria — **AUMENTA le quarantene**: un claim che
dice «*il valore è 2*» oggi combacia con una fonte che dice «2%», domani no, e
`L4.1` parlerebbe.

⚠️ E la coda di revisione è già a **1057 contro una soglia di 500**, in ingresso
**cinque volte** l'uscita (misura di @ws6). ⇒ **una cura che aggiunge quarantene
va misurata PRIMA, non dopo.** Questo banco misura il costo; non cura niente.

LA DOMANDA, precisa: fra i fatti che il prodotto ha **già ammesso**, quanti
hanno un claim con `N%` il cui `N` **non compare come percentuale nella fonte**
ma **compare come numero nudo**? Sono quelli il cui verdetto `L4.1`
**potrebbe ribaltarsi** dando a `%` un'unità.

LA PREDIZIONE, scritta prima di eseguire: **sotto il 2%** dei fatti esaminati.
Sopra il 10% la cura non va fatta senza una decisione di Aurelio, perché
quarantinare centinaia di fatti già ammessi non è un dettaglio tecnico.

CONTROLLO CHE DEVE POTER FALLIRE: se nessun claim del corpus contiene una
percentuale, il banco non misura niente e non stampa una quota.

    sola lettura (`mode=ro`) · percorso chiesto a `CONFIG.semantic_db`
    NESSUNA scrittura sullo store di Aurelio

    python docs/stato-reale/banchi/ws3-quanto-costerebbe-dare-un-unita-alle-percentuali.py
"""

from __future__ import annotations

import re
import sqlite3

#: «2%», «2 %», «97,5%» — il valore normalizzato col punto decimale.
_PERC = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
#: lo stesso numero NON seguito da `%`
def _nudo_re(n: str) -> re.Pattern[str]:
    return re.compile(r"(?<![\d.,])" + re.escape(n) + r"(?![\d.,])(?!\s*%)")


_UNA_RIGA = re.compile(r"\s+")


def _perc(t: str) -> set[str]:
    return {m.group(1).replace(",", ".") for m in _PERC.finditer(t)}


def main() -> int:
    from verimem.config import CONFIG

    db = str(CONFIG.semantic_db)
    print("  REGIME, dichiarato E misurato:")
    print(f"    store: {db}")
    print("    SOLA LETTURA (mode=ro) · nessuna scrittura · store di Aurelio")
    print("    NESSUNA CURA in questo file: misura il costo, non lo paga.")

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        righe = list(con.execute(
            "SELECT proposition, grounding_span FROM facts "
            "WHERE grounding_span IS NOT NULL AND length(grounding_span) > 0 "
            "AND grounding_score >= 90"))
    finally:
        con.close()
    print(f"    fatti ammessi con span e grounding >= 90: {len(righe)}")

    con_perc = 0
    a_rischio: list[tuple[str, str, str]] = []
    perc_confermata = 0
    esaminati = 0
    for prop, span in righe:
        if not prop or not span:
            continue
        esaminati += 1
        pc = _perc(prop)
        if not pc:
            continue
        con_perc += 1
        ps = _perc(span)
        for n in sorted(pc):
            if n in ps:
                perc_confermata += 1
                continue          # la fonte porta la STESSA percentuale: nessun cambio
            # il numero non e' una percentuale nella fonte: compare NUDO?
            if _nudo_re(n).search(span):
                a_rischio.append((n, prop, span))
                break

    print("\n  ══ IL CONTO ══")
    print(f"     esaminati ................................. {esaminati}")
    print(f"     claim che contengono una PERCENTUALE ...... {con_perc}"
          f"   ({100.0 * con_perc / max(esaminati, 1):.1f}%)")
    # ⚠️ ETICHETTA CORRETTA dopo la prima esecuzione: diceva «di questi»
    # riferito ai FATTI e stampava 43 su 39 — perche' contava le PERCENTUALI,
    # e un claim con due percentuali conta due volte. Il numero era giusto e
    # l'etichetta nominava la popolazione SBAGLIATA. E' la terza volta oggi
    # che un mio misuratore misura bene e RIFERISCE male: l'etichetta deve
    # nominare la popolazione CONTATA.
    print("     ► occorrenze di percentuale CONFERMATE come")
    print(f"       percentuale nella fonte ................. {perc_confermata}"
          f"   (occorrenze, NON fatti: un claim con due percentuali conta due volte)")
    print(f"     ► A RISCHIO DI RIBALTAMENTO ............... {len(a_rischio)}"
          f"   ({100.0 * len(a_rischio) / max(esaminati, 1):.2f}% degli esaminati)")

    if con_perc == 0:
        print("\n     CONTROLLO CADUTO: nessun claim con una percentuale ⇒ il banco")
        print("     non misura niente. NESSUNA QUOTA.")
        return 1

    if a_rischio:
        print("\n  I CASI A RISCHIO (tutti, se sono pochi — vanno LETTI, non contati):")
        for n, prop, span in a_rischio[:12]:
            # ⚠️ Stesso bug del banco delle date, altra forma: la regex era
            # `.s+` — un carattere QUALSIASI seguito da `s` — invece di `\s+`.
            # Non tocca i conteggi, solo la stampa.
            c1 = _UNA_RIGA.sub(" ", prop)
            s1 = _UNA_RIGA.sub(" ", span)
            print(f"     · {n}%  claim: {c1[:78]}")
            print(f"            span : {s1[:78]}")
        if len(a_rischio) > 12:
            print(f"     … e altri {len(a_rischio) - 12} non stampati")

    quota = 100.0 * len(a_rischio) / max(esaminati, 1)
    print("\n  ══ VERDETTO sulla PREDIZIONE ══")
    print(f"     previsto: SOTTO il 2%   ·   misurato: {quota:.2f}%")
    if quota < 2:
        print("     RETTA: il costo della cura e' piccolo e leggibile a mano.")
        print("     ⇒ si puo' proporre la cura portando i casi, non solo il numero.")
    elif quota < 10:
        print("     SBAGLIATA nella taglia, ma sotto il 10%: la cura resta")
        print("     proponibile, dichiarando quanti fatti gia' ammessi tocca.")
    else:
        print("     FALSIFICATA: sopra il 10%. La cura NON va fatta senza una")
        print("     decisione di Aurelio: quarantinare centinaia di fatti gia'")
        print("     ammessi non e' un dettaglio tecnico.")

    print("\n  ⚠️ LIMITI: e' un PROXY sul testo, non un'esecuzione del gate — dice")
    print("     dove il verdetto POTREBBE cambiare, non che cambierebbe: il")
    print("     verdetto finale dipende anche dal giudice. «grounding alto» non e'")
    print("     «vero». Lo span e' TRONCATO a 400 caratteri, quindi una percentuale")
    print("     confermata piu' avanti nella fonte qui risulta assente ⇒ la quota")
    print("     e' verosimilmente una SOVRASTIMA. Il corpus e' fatto di output di")
    print("     strumenti, non di contratti: su prosa legale le percentuali")
    print("     peserebbero di piu'. E si muove mentre lo misuri: siamo in otto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
