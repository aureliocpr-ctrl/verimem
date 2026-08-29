"""Il giudice respinge una parafrasi FEDELE: era un caso o e' una classe?

In `a21d059c` una riga saltava all'occhio: la serie `impianto` dava **0,1** a
una **riformulazione fedele** — «*a parte la manutenzione semestrale, l'impianto
lavora senza interruzioni*» contro la fonte «*fermato ogni sei mesi per la
manutenzione e produce a ciclo continuo nel resto dell'anno*». Dicono la stessa
cosa, e il giudice la metteva **peggio della negazione vera** (1,1).

Era **1 caso su 3**, e l'ho riportato come osservazione. Ma la posta e' alta: se
fosse una **classe**, il prodotto **punirebbe chi scrive con parole proprie** —
e sarebbe grave quanto il buco opposto, perche' un agente che riformula per
sintetizzare si vedrebbe **quarantinare un fatto VERO**.

DIECI PARAFRASI FEDELI, ognuna con un meccanismo linguistico diverso:

    1 passiva→attiva      6 doppia negazione→affermativa
    2 sinonimi            7 quantificatore equivalente
    3 ordine invertito    8 soggetto/complemento scambiati (stesso senso)
    9 nominalizzazione   10 condensazione di due frasi in una
    5 «a parte X»→«tranne X»   4 perifrasi

⚠️ **NON sono claim piu' deboli ne' piu' forti**: ognuno afferma **esattamente**
cio' che la fonte afferma, con altre parole. Se il giudice misura
**implicazione**, devono stare **tutti alti**.

LA PREDIZIONE, scritta prima di eseguire: **al piu' 1 su 10** scende sotto 20 —
cioe' `impianto G2` era **un caso**, non una classe.

CONDIZIONE DI FALSIFICAZIONE: se **3 o piu' su 10** scendono sotto 20, e' una
**classe**, la mia predizione cade, e il reperto diventa grave quanto il buco
dell'irrilevante — con la differenza che questo colpisce i fatti **VERI**.

CONTROLLO CHE DEVE POTER FALLIRE: per ogni fonte, il claim **identico** al testo
della fonte deve stare **alto**. Se cadesse anche quello, non misurerei la
parafrasi: misurerei fonti scritte male, e ogni numero sarebbe illeggibile.

🟢 **ESITO: PREDIZIONE RETTA — `impianto G2` era UN CASO, non una classe.**

    meccanismo            identico  parafrasi  esito
    passiva->attiva          100.0       96.6  ENTRA
    sinonimi                 100.0       99.6  ENTRA
    ordine invertito          99.9       99.8  ENTRA
    perifrasi                 99.8       98.7  ENTRA
    a parte->tranne          100.0       99.1  ENTRA
    doppia negazione          99.8       97.6  fermata   <---
    quantificatore            99.6      100.0  ENTRA
    scambio ruoli             99.9       98.2  ENTRA
    nominalizzazione          99.9       96.8  ENTRA
    condensazione            100.0      100.0  ENTRA

**Controllo retto 10/10** · **parafrasi respinte dal giudice: 0/10** (tutte fra
96,6 e 100,0). ⇒ **Il giudice regge le riformulazioni fedeli**, e il caso
`impianto G2` resta un'**osservazione isolata**. Buona notizia, e la do per
prima.

🔴 **MA UNA RIGA VA LETTA: `doppia negazione` prende 97,6 ED E' FERMATA.**
Ho sospettato un artefatto del mio banco — scrivo l'identico e poi la parafrasi
nello stesso store, e un layer di contraddizione poteva vederli in conflitto. **A/B
su store pulito contro store gia' popolato: stesso esito** (`quarantined`,
`qb='L1'`, layer `L1.13`). ⇒ **non e' il mio banco.**

`L1.13` e' il **«completion claim detector»** (`anti_confab_gate.py:1453`):
prende le dichiarazioni di **completamento** prive di criteri di chiusura
(`task:_closed` / `pytest:_PASS` / `dod:_met`). La parafrasi era «*Di notte il
portone e' sempre **chiuso**»* — e **`chiuso` viene letto come «task chiuso»,
non come «serrato»**. **Una polisemia del participio.**

🔑 **Il punto che conta**: **`L1` e' lessicale e NON consulta la fonte.** Qui la
fonte diceva **esattamente la stessa cosa** («*non resta mai aperto durante la
notte*»), il giudice l'aveva riconosciuta a **97,6**, e il claim e' stato
quarantinato lo stesso. ⇒ **Il gate puo' fermare un fatto VERO e SUPPORTATO per
un'ambiguita' di vocabolario.**
📌 E la classe e' **gia' nota agli autori** in un'altra faccia: il commento a
`anti_confab_gate.py:1599` racconta che «*nove detector su dodici leggevano «Il
modulo NON funziona in produzione» come la dichiarazione che funziona*» — la
**negazione** e' stata curata, la **polisemia** e' l'altra faccia della stessa
moneta. Esiste gia' anche un'esenzione (`_is_honest_reported`), quindi il
meccanismo per gestirlo c'e'.

⚠️ **NON lo gonfio: e' 1 caso su 10**, e «chiuso» e' genuinamente ambiguo in
italiano. Lo lascio agli atti come **osservazione**, non come difetto proposto.
🔑 E vale la pena notare che i **due numeri del banco divergono**: **respinte dal
giudice 0/10**, **fermate dal gate 1/10**. Averli tenuti separati e' cio' che ha
fatto emergere il caso — un numero solo avrebbe detto «tutto bene» oppure «una
su dieci fallisce», e nessuna delle due sarebbe stata vera.

REGIME: store TEMPORANEO, cross-encoder locale (nessuna API esterna). Lo store
di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-la-parafrasi-fedele-e-un-caso-o-una-classe.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

SOTTO = 20.0

#: (meccanismo, fonte, claim IDENTICO alla fonte, PARAFRASI fedele)
CASI: list[tuple[str, str, str, str]] = [
    ("passiva->attiva",
     "La pratica e' stata approvata dal comitato tecnico.",
     "La pratica e' stata approvata dal comitato tecnico.",
     "Il comitato tecnico ha approvato la pratica."),
    ("sinonimi",
     "Il magazzino e' rimasto chiuso per l'intera giornata di lunedi'.",
     "Il magazzino e' rimasto chiuso per l'intera giornata di lunedi'.",
     "Lunedi' il deposito e' stato serrato per tutto il giorno."),
    ("ordine invertito",
     "Il corso si tiene in aula e prevede una prova finale.",
     "Il corso si tiene in aula e prevede una prova finale.",
     "Il corso prevede una prova finale e si tiene in aula."),
    ("perifrasi",
     "Il fornitore sostiene le spese di trasporto.",
     "Il fornitore sostiene le spese di trasporto.",
     "Le spese di trasporto sono a carico del fornitore."),
    ("a parte->tranne",
     "L'ufficio e' aperto tutti i giorni a parte la domenica.",
     "L'ufficio e' aperto tutti i giorni a parte la domenica.",
     "L'ufficio e' aperto ogni giorno tranne la domenica."),
    ("doppia negazione",
     "Il portone non resta mai aperto durante la notte.",
     "Il portone non resta mai aperto durante la notte.",
     "Di notte il portone e' sempre chiuso."),
    ("quantificatore",
     "Tutti i dipendenti hanno ricevuto la comunicazione.",
     "Tutti i dipendenti hanno ricevuto la comunicazione.",
     "Nessun dipendente e' rimasto senza la comunicazione."),
    ("scambio ruoli",
     "Il contratto vincola il fornitore alla consegna puntuale.",
     "Il contratto vincola il fornitore alla consegna puntuale.",
     "Il fornitore e' vincolato dal contratto a consegnare puntualmente."),
    ("nominalizzazione",
     "L'impianto viene ispezionato ogni sei mesi.",
     "L'impianto viene ispezionato ogni sei mesi.",
     "L'ispezione dell'impianto avviene con cadenza semestrale."),
    ("condensazione",
     "La sala e' dotata di proiettore. La sala dispone anche di microfoni.",
     "La sala e' dotata di proiettore e dispone anche di microfoni.",
     "La sala ha proiettore e microfoni."),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print(f"  «respinta» = punteggio sotto {SOTTO:.0f}")
    mem = Memory(str(tmp / "para.db"))
    n = 0

    def punteggio(claim: str, fonte: str) -> tuple[float, bool]:
        nonlocal n
        n += 1
        r = mem.add(claim, topic=f"pa/{n}", source=fonte, validate="full")
        gs = r.get("grounding_score")
        return (-1.0 if gs is None else float(gs),
                str(r.get("status")) != "quarantined")

    print(f"\n  {'meccanismo':<20} {'identico':>9} {'parafrasi':>10}  esito")
    print("  " + "-" * 58)
    ctrl_ok = 0
    respinte = 0
    fermate = 0
    for mecc, fonte, identico, parafrasi in CASI:
        gs_id, _ = punteggio(identico, fonte)
        gs_pa, entra = punteggio(parafrasi, fonte)
        if gs_id >= 80.0:
            ctrl_ok += 1
        if gs_pa < SOTTO:
            respinte += 1
        if not entra:
            fermate += 1
        marca = "  <<< RESPINTA" if gs_pa < SOTTO else ""
        print(f"  {mecc:<20} {gs_id:>9.1f} {gs_pa:>10.1f}  "
              f"{'ENTRA' if entra else 'fermata'}{marca}")

    tot = len(CASI)
    print(f"\n  [1] CONTROLLO — il claim IDENTICO sta alto: {ctrl_ok}/{tot}")
    if ctrl_ok < tot:
        print("      CONTROLLO CADUTO: anche il claim identico alla fonte non")
        print("      passa ⇒ misuro fonti scritte male, non la parafrasi.")
        print("      NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     parafrasi RESPINTE (sotto {SOTTO:.0f}) ... {respinte}/{tot}")
    print(f"     parafrasi FERMATE dal gate ......... {fermate}/{tot}")
    if respinte <= 1:
        print("     PREDIZIONE RETTA: `impianto G2` era UN CASO, non una")
        print("     classe. Il giudice regge le riformulazioni fedeli, e il")
        print("     reperto va tenuto come osservazione isolata.")
    elif respinte >= 3:
        print("     PREDIZIONE FALSIFICATA: e' una CLASSE. Il prodotto respinge")
        print("     fatti VERI riformulati ⇒ chi scrive con parole proprie viene")
        print("     punito, ed e' grave quanto il buco dell'irrilevante — con la")
        print("     differenza che questo colpisce i fatti VERI.")
    else:
        print("     ZONA GRIGIA (2 su 10): non e' un caso isolato e non e' una")
        print("     classe. Serve una popolazione piu' larga prima di dire")
        print("     qualunque cosa — e NON la dico.")

    print(f"\n  ⚠️ LIMITI: {n} celle, 10 meccanismi, italiano, un giudice")
    print("     (cross-encoder locale). «Parafrasi fedele» e' un giudizio MIO:")
    print("     un linguista potrebbe contestare qualche coppia, e il numero")
    print("     cambierebbe di conseguenza.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
