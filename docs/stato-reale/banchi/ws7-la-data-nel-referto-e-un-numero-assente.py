# -*- coding: utf-8 -*-
"""LA DATA DENTRO UN REFERTO E' UN NUMERO CHE LA FONTE NON CONTIENE

PERCHE' ESISTE. Ieri notte alle 02:13 `verimem save` ha quarantinato un fatto MIO
(`grounded 99.7`) e il rimedio diceva «un numero che la fonte non dice». Il claim era
*«Nel banco ws7 del 29/08 i miei referti ammessi sono 5/5»* e **«5/5» ERA nella source**:
ho scritto nel registro «non so perche'» e ho perso due minuti in un A/B sbagliato
(store temporaneo, «5 su 5» invece di «5/5») cercando la causa dove non era.

LEGGENDO `valori_non_nella_fonte` invece di costruire banchi, la risposta e' immediata:

    numeri visti nel claim  ->  5.0 · 8.0 · 29.0        <- «29/08», la DATA
    numeri nella fonte      ->  5.0 · 99.47 · 99.98 · 314.0 · 900.0
    verdetto L4.1           ->  ValoreAssente(8.0, '08') · ValoreAssente(29.0, '29')

⇒ **`L4.1` aveva RAGIONE e la mia accusa era falsa**: non diceva che «5/5» manca —
diceva che manca la DATA. Togliendo «ws7 del 29/08» dal claim, non ha piu' nulla da dire.

QUESTO BANCO MISURA LE DUE COSE CHE RESTANO, e sono diverse fra loro:

  A. **QUANTO E' GENERALE**: un referto vero che DATA la propria misura viene fermato
     dalla data, anche quando ogni altra cifra e' nella fonte? Popolazione: sei referti
     nella forma che `O3` ci impone, la stessa fonte, **con e senza la data**.
     E' un A/B a variabile singola: cambia SOLO la data.

  B. **LA RICEVUTA NOMINA IL NUMERO?** La funzione restituisce `ValoreAssente(valore,
     unita, testo)` — **sa quale**. Il messaggio che l'utente riceve dice «un numero».
     Se il nome non arriva alla porta, l'informazione esiste e non viene consegnata,
     e chi legge cerca nel posto sbagliato: **e' quello che e' successo a me.**

CONTROLLO CHE DEVE POTER FALLIRE: un referto con una cifra VERAMENTE inventata deve
restare fermato anche senza data — altrimenti il banco starebbe misurando un layer
spento e ogni conclusione sarebbe vuota.

    python docs/stato-reale/banchi/ws7-la-data-nel-referto-e-un-numero-assente.py

Livello dichiarato: **funzione pubblica** `verimem.valore_non_nella_fonte.valori_non_nella_fonte`
(il layer `L4.1`), non la porta del prodotto. Nessuno store, nessun modello: e' un
confronto lessicale deterministico, quindi il risultato non dipende dall'embedder.
"""

from __future__ import annotations

import sys

from verimem.valore_non_nella_fonte import valori_non_nella_fonte

#: la fonte: l'uscita grezza di un banco, come `O3` impone di passarla. NON contiene date.
FONTE = """  === i miei referti, passati al gate (store temporaneo) ===
  OK  99.98 model_claim  Su cinque righe del log dei bloccati P1 nomina lo schermo 5 su 5.
  OK  99.47 model_claim  Lo span tenuto e' 314 caratteri su 5250 della fonte.
  OK  99.47 model_claim  Lo span non e' contiguo nella fonte.

  CONTROLLO (900 invece di 314): quarantined  retto

  => miei referti ammessi: 5/5"""

#: sei referti VERI: ogni cifra sta nella fonte. Il primo elemento e' la forma DATATA
#: (come li scriviamo davvero), il secondo la stessa frase senza la data.
COPPIE = [
    ("Nel banco del 29/08 i miei referti ammessi sono 5/5.",
     "I miei referti ammessi sono 5/5."),
    ("Il 29/08 lo span tenuto e' 314 caratteri su 5250 della fonte.",
     "Lo span tenuto e' 314 caratteri su 5250 della fonte."),
    ("Misurato il 29/08: il controllo con 900 invece di 314 resta quarantined.",
     "Il controllo con 900 invece di 314 resta quarantined."),
    ("Il 29/08 il grounding del primo referto e' 99.98.",
     "Il grounding del primo referto e' 99.98."),
    ("Alle 02:13 del 29/08 lo span non e' contiguo nella fonte.",
     "Lo span non e' contiguo nella fonte."),
    ("Referto del 29/08: 5 righe su 5 sono state ammesse.",
     "5 righe su 5 sono state ammesse."),
]

#: controllo che deve poter fallire: cifra VERAMENTE inventata, senza data.
INVENTATO = "Lo span tenuto e' 777 caratteri su 5250 della fonte."


def _fermato(claim: str) -> list:
    return valori_non_nella_fonte(claim, FONTE)


def main() -> int:
    # il controllo prima di tutto: se il layer fosse spento, il resto non direbbe nulla
    inv = _fermato(INVENTATO)
    if not inv:
        print("  CONTROLLO CADUTO: la cifra inventata 777 NON e' stata rilevata")
        print("  ⇒ il layer non sta lavorando, ogni altro numero di questo banco e' vuoto")
        return 1
    print(f"  controllo retto: la cifra inventata 777 e' rilevata -> {inv[0].testo!r}\n")

    con_data = senza_data = 0
    nomi_dati = 0
    print("  == A/B a variabile singola: la STESSA frase, con e senza la data ==\n")
    for datato, nudo in COPPIE:
        a, b = _fermato(datato), _fermato(nudo)
        con_data += bool(a)
        senza_data += bool(b)
        quali = " ".join(repr(x.testo) for x in a) or "—"
        print(f"  {'🔴' if a else '🟢'} con data   {quali:20} {datato[:58]}")
        print(f"  {'🔴' if b else '🟢'} senza data {' '.join(repr(x.testo) for x in b) or '—':20} {nudo[:58]}")
        # B: la funzione NOMINA il numero mancante?
        if a and all(getattr(x, "testo", None) for x in a):
            nomi_dati += 1

    n = len(COPPIE)
    print("\n  " + "=" * 74)
    print(f"  A. fermati CON la data     : {con_data}/{n}")
    print(f"     fermati SENZA la data   : {senza_data}/{n}   <- stessa frase, stessa fonte")
    print(f"  B. la FUNZIONE nomina il numero assente in {nomi_dati}/{con_data} dei casi fermati")
    print("     ⇒ l'informazione ESISTE nel layer: se il messaggio all'utente dice solo")
    print("       «un numero», e' la CONSEGNA a perderla, non la misura.")
    print("  " + "=" * 74)
    if con_data and not senza_data:
        print("\n  ⇒ La variabile e' la DATA, e da sola basta a far cadere un referto VERO")
        print("    in cui ogni altra cifra sta nella fonte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
