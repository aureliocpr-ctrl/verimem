"""LA FONTE LUNGA, E DOVE STA L'EVIDENZA DENTRO DI ESSA.

\U0001f4cc **IL PEZZO CHE IL CORPUS NON PUO' DARE.** `W7-96` ha trovato che nel
DB **le fonti lunghe non esistono**: `grounding_span` e' un estratto (budget
**400**, massimo osservato **932** su 7030). ⇒ Il reperto di **@ws5** delle
18:41 — *«su fonte LUNGA e tabellare il gate e' rovesciato»* — **non e'
misurabile pescando dal corpus**, perche' la variabile e' tagliata prima che il
fatto arrivi al DB. Si misura **passando la fonte lunga direttamente al gate**.

Gliel'ho offerto sul canale e non l'ha raccolto: lo misuro io **portandogli i
numeri**, non togliendogli il reperto.

\U0001f511 **E IL DISEGNO HA DUE DIMENSIONI, NON UNA.** «Fonte lunga» da sola
non e' una spiegazione: il gate **seleziona una porzione rilevante**
(`select_relevant_span`, `W7-90`). Quindi la domanda vera e'::

    la fonte e' LUNGA          →  quanto?    300 · 800 · 2000 · 5000 caratteri
    l'evidenza sta DOVE?       →  in TESTA, in MEZZO, in CODA

Se il punteggio cade solo quando l'evidenza sta **in coda**, il difetto non e'
la lunghezza: e' che **il selettore non va a prenderla**. Se cade in tutte le
posizioni al crescere della lunghezza, e' il **rumore** che annega il segnale.
**Sono due difetti diversi e si curano diversamente.**

ATTESA DICHIARATA PRIMA: **cadra' solo con l'evidenza in CODA su fonte lunga**,
perche' un selettore ingenuo prende un prefisso. ⚠️ **Se cade anche con
l'evidenza in TESTA, e' il rumore e non la posizione** — lo dico con la stessa
forza. ⚠️ **Se non cade mai, il perimetro di @ws5 non si riproduce da qui**, e
va detto **senza chiamarlo una smentita**: la sua fonte poteva avere altre
proprieta'.

CONTROLLI CHE POSSONO FALLIRE:
 (1) ✅ **il caso base deve passare**: fonte corta con l'evidenza dentro ⇒
     punteggio alto. Se no, il claim e' malformato e mi fermo.
 (2) 🪞 **il riempimento e' NEUTRO e sempre lo stesso**: frasi vere che non
     parlano dell'argomento. Se il riempimento contraddicesse il claim,
     misurerei una contraddizione, non la lunghezza.
 (3) ⚖️ **una sola variabile per cella**: a lunghezza fissa cambio solo la
     posizione, a posizione fissa solo la lunghezza.
 (4) ⚠️ **PREFLIGHT sul moat** (`W7-87`).

    python -u docs/stato-reale/banchi/la-fonte-lunga-e-dove-sta-l-evidenza.py
"""

from __future__ import annotations

import sys
import time

CUT = 40.0
CLAIM = "Il collaudo della linea 4 ha prodotto 318 pezzi conformi."
EVIDENZA = ("Verbale di collaudo: la linea 4 ha prodotto 318 pezzi conformi"
            " durante la sessione del mattino.")
#: riempimento NEUTRO: vero, verboso, e che non parla di linee ne' di pezzi.
RIEMPIMENTO = (
    "La riunione operativa si tiene ogni lunedi nella sala al primo piano. "
    "Il parcheggio interno resta aperto fino alle venti e trenta. "
    "La mensa propone due primi e un secondo, con menu affisso all'ingresso. "
    "Le pratiche amministrative passano dall'ufficio protocollo. "
    "Il corso di aggiornamento sulla sicurezza dura quattro ore. "
    "La rassegna stampa viene distribuita per posta elettronica ogni mattina. "
    "Gli armadietti dello spogliatoio sono assegnati per matricola. "
    "Il servizio di navetta collega la stazione allo stabilimento. ")

#: ⚠️ IL SECONDO RIEMPIMENTO, aggiunto il 31/08 alle 00:35 DOPO la prima
#: esecuzione: col riempimento DISCORSIVO il gate non cade mai (99,90-99,98
#: fino a 12000 caratteri, in ogni posizione). Ma il reperto di @ws5 dice
#: «lunga E TABELLARE», e io avevo variato **una meta' sola**. Questo e' lo
#: stesso banco con l'altra meta': riempimento tabellare, tutto il resto
#: identico — una variabile alla volta.
RIEMPIMENTO_TAB = (
    "reparto     turno   pezzi   scarti   esito\n"
    "A-11        mattino   204        3   ok\n"
    "A-12        mattino   198        1   ok\n"
    "B-03        pomeriggio 221       5   ok\n"
    "B-04        pomeriggio 187       2   ok\n"
    "C-21        notte      165       4   ok\n"
    "C-22        notte      173       0   ok\n"
    "D-31        mattino    209       6   ok\n"
    "D-32        pomeriggio 194       1   ok\n")


def _fonte(lunghezza: int, posizione: str, riempitivo: str = "") -> str:
    """Fonte di lunghezza voluta, con l'evidenza in testa, in mezzo o in coda.

    Il riempimento e' lo stesso testo neutro ripetuto: cambia solo QUANTO ce
    n'e' e DOVE sta l'evidenza rispetto a esso.
    """
    base = riempitivo or RIEMPIMENTO
    resto = max(0, lunghezza - len(EVIDENZA))
    riemp = (base * (resto // len(base) + 1))[:resto]
    if posizione == "testa":
        return EVIDENZA + " " + riemp
    if posizione == "coda":
        return riemp + " " + EVIDENZA
    meta = len(riemp) // 2
    return riemp[:meta] + " " + EVIDENZA + " " + riemp[meta:]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.local_grounding import judge_state, warm_local_judge_async
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print("  -- preflight: il moat deve essere CALDO")
    warm_local_judge_async()
    t0 = time.time()
    stato = judge_state()
    while stato == "warming" and time.time() - t0 < 180:
        time.sleep(2)
        stato = judge_state()
    print(f"     `judge_state()` = {stato!r}  dopo {time.time() - t0:.1f}s")
    if stato != "ready":
        print("NON RIUSCITO: giudice non pronto, misurerei il warmup.")
        return 1

    def _g(fonte: str) -> float:
        try:
            res = run_validation_gate(
                proposition=CLAIM, verified_by=None, topic="banco/fonte-lunga",
                agent=None, source=fonte, ground_write=True)
        except Exception:  # noqa: BLE001
            return -1.0
        return (float(res.grounding_score)
                if res.grounding_score is not None else -1.0)

    # (1) il caso base
    base = _g(EVIDENZA)
    print(f"\n  -- (1) caso base: sola evidenza ({len(EVIDENZA)} char)"
          f"  ->  {base:.2f}")
    if base < 80:
        print("     CADUTO: il claim non passa nemmeno con la sola evidenza.")
        print("     E' malformato: mi fermo invece di misurare la lunghezza.")
        return 1

    lunghezze = [300, 800, 2000, 5000, 12000]
    posizioni = ["testa", "mezzo", "coda"]
    # Due riempimenti, una variabile alla volta: il DISCORSIVO isola
    # lunghezza+posizione, il TABELLARE aggiunge la meta' che manca al
    # reperto di @ws5.
    tabelle: dict[str, dict[tuple[int, str], float]] = {}
    for eti, riemp in (("DISCORSIVO", RIEMPIMENTO),
                       ("TABELLARE", RIEMPIMENTO_TAB)):
        print(f"\n  -- riempimento {eti}")
        print(f"     {'lunghezza':>10}"
              + "".join(f"{p:>12}" for p in posizioni))
        tab: dict[tuple[int, str], float] = {}
        for L in lunghezze:
            riga = f"     {L:>10}"
            for p in posizioni:
                g = _g(_fonte(L, p, riemp))
                tab[(L, p)] = g
                marca = "🔴" if g < CUT else ("🟡" if g < 80 else "  ")
                riga += f"{marca}{g:>10.2f}"
            print(riga)
        tabelle[eti] = tab
    tabella = tabelle["TABELLARE"]
    print("\n  -- il confronto fra i due riempimenti, a parita' di tutto"
          " il resto")
    for L in lunghezze:
        for p in posizioni:
            d, t_ = tabelle["DISCORSIVO"][(L, p)], tabelle["TABELLARE"][(L, p)]
            if abs(d - t_) >= 5.0:
                print(f"     {L:>6} {p:<6} discorsivo {d:6.2f} contro"
                      f" tabellare {t_:6.2f}   Δ {t_ - d:+.2f}")
    if all(abs(tabelle["DISCORSIVO"][k] - tabelle["TABELLARE"][k]) < 5.0
           for k in tabelle["DISCORSIVO"]):
        print("     nessuna cella differisce di 5 punti: **la forma del"
              " riempimento non conta**.")

    print("\n  == LA RIGA CHE CONTA")
    # a lunghezza massima, la posizione conta?
    Lmax = lunghezze[-1]
    t, c = tabella[(Lmax, "testa")], tabella[(Lmax, "coda")]
    caduti_testa = [L for L in lunghezze if tabella[(L, "testa")] < CUT]
    caduti_coda = [L for L in lunghezze if tabella[(L, "coda")] < CUT]

    if not caduti_testa and not caduti_coda:
        print(f"     🟢 **NON CADE MAI**, fino a {Lmax} caratteri e in ogni"
              " posizione.")
        print("     ⇒ **Il perimetro di @ws5 non si riproduce da qui** — e"
              " NON e' una")
        print("     smentita: la sua fonte poteva avere altre proprieta'"
              " (tabellare,")
        print("     contenuto in conflitto, claim diverso). **Una non-misura,"
              " non un no.**")
    elif caduti_coda and not caduti_testa:
        print("     🔴 **E' LA POSIZIONE, NON LA LUNGHEZZA**: con l'evidenza"
              " in CODA cade")
        print(f"     a {caduti_coda}, in TESTA non cade mai."
              f" A {Lmax}: testa {t:.2f} contro coda {c:.2f}.")
        print("     ⇒ **Il selettore non va a prendere l'evidenza lontana.**"
              " Si cura")
        print("     nel selettore, non nel cut.")
    elif caduti_testa:
        print(f"     🟡 **CADE ANCHE IN TESTA** (a {caduti_testa}): non e' la")
        print("     posizione, e' il **rumore** che annega il segnale al"
              " crescere")
        print("     della fonte. La mia attesa e' falsificata e lo dico.")

    print("\n  ⚠️ COSA NON DICE: **un solo claim e due riempimenti** — un altro")
    print("  contenuto puo' dare altro · le soglie di lunghezza sono mie · e")
    print("  soprattutto **il riempimento e' NEUTRO**: non contraddice il"
          " claim e")
    print("  non parla dell'argomento. Una fonte lunga che dice cose"
          " CONFLIGGENTI")
    print("  e' un'altra cosa, e questo banco non la tocca.")
    print("  \U0001f4cc Cio' che il banco ESCLUDE, e serve a chi cerca la"
          " causa altrove:")
    print("  **la lunghezza (fino a 12000), la posizione dell'evidenza, e la")
    print("  forma tabellare del riempimento** non fanno cadere il gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
