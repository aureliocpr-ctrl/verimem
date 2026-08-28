# -*- coding: utf-8 -*-
"""IL CASO ME LO SONO PROCURATO USANDO IL PRODOTTO, non costruendolo.

Alle 23:03 ho salvato con `verimem save` un fatto VERO la cui source era
l'output di `scripts/controlla_registro.py`. Il prodotto l'ha quarantinato, e
la ricevuta diceva:

    L4.1 - il claim afferma un valore che la fonte non contiene: 23
    L4.2 - il claim riusa un numero della fonte riferendolo a un'altra
           grandezza: 6 qui e' «identificativi», nella fonte «in»

Su `L4.1` il gate ha ragione e l'errore e' MIO: avevo scritto «Alle 23 del 28
agosto» e la source non contiene l'ora. Lo dico prima di tutto il resto.

Su `L4.2` invece la fonte e' una TABELLA ALLINEATA:

    BLOCCA  identificativo di sessione         6 in   3 file

e l'etichetta della grandezza sta a SINISTRA del numero, mentre a destra c'e'
la parola «in». Il layer ha letto «in» come grandezza.

⇒ IPOTESI: `valori_riusati_da_altro_contesto` legge il vicinato **a destra**, e
su un output tabellare a destra non c'e' l'etichetta. Se e' cosi', il layer
sbaglia su **ogni referto di strumento** — cioe' sulla forma di source che noi
usiamo piu' spesso.

CONTROLLI CHE POSSONO FALLIRE:
 (1) IL CONTROLLO POSITIVO: il caso che il layer nasce per cogliere («14
     valvole» quando la fonte dice «14 operai», dal commento a
     `anti_confab_gate.py:2505`) DEVE essere segnalato. Se tace anche li',
     sto misurando un layer spento e il resto non vale niente.
 (2) se anche la fonte con l'etichetta a DESTRA viene segnalata, la mia
     ipotesi sulla posizione CADE: non e' il lato, e' altro.

    python -u docs/stato-reale/banchi/L4-2-su-una-tabella-legge-la-grandezza-sbagliata.py
"""

from __future__ import annotations

import sys

# il claim vero, quello che ho salvato davvero (senza l'ora, che era l'errore mio)
CLAIM = "Il controllo sul package verimem riporta 6 identificativi di sessione in 3 file."

FONTI = [
    # (nome, fonte, atteso secondo l'ipotesi)
    ("A tabella allineata (il caso VERO)",
     "artefatto: verimem\nfile .py esaminati: 421\n\n"
     "  BLOCCA  identificativo di sessione         6 in   3 file\n"
     "    ok   nome proprio di sessione           0 in   0 file",
     "segnala (etichetta a SINISTRA)"),
    ("B etichetta a DESTRA del numero",
     "artefatto: verimem\nfile .py esaminati: 421\n\n"
     "  BLOCCA  6 identificativi di sessione in 3 file\n"
     "    ok   0 nomi propri di sessione in 0 file",
     "tace se conta la posizione"),
    ("C prosa, etichetta a destra",
     "Il controllo sul package verimem riporta 6 identificativi di sessione "
     "in 3 file, e 0 nomi propri.",
     "tace"),
    ("D tabella, ma senza la parola 'in'",
     "artefatto: verimem\n\n"
     "  BLOCCA  identificativo di sessione         6       3 file",
     "?"),
]

# il controllo positivo: il caso del commento a anti_confab_gate.py:2505
POSITIVO_CLAIM = "L'impianto ha 14 valvole."
POSITIVO_FONTE = "Nel reparto lavorano 14 operai su tre turni."


def main() -> int:
    try:
        from verimem import vicinato_del_valore as vv
        from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1
    print(f"  codice sotto misura: {vv.__file__}")

    print("\n  -- CONTROLLO (1): il layer e' ACCESO?")
    pos = valori_riusati_da_altro_contesto(POSITIVO_CLAIM, POSITIVO_FONTE)
    if not pos:
        print("     CADUTO - il layer TACE sul caso che nasce per cogliere")
        print(f"       claim: {POSITIVO_CLAIM!r}")
        print(f"       fonte: {POSITIVO_FONTE!r}")
        print("     Sto misurando un layer spento: il resto non vale niente.")
        return 1
    for r in pos:
        print(f"     acceso - segnala: {r.valore:g} qui «{r.nel_claim}», "
              f"nella fonte «{r.nella_fonte}»")

    print(f"\n  == IL CASO VERO e le sue varianti")
    print(f"     claim: {CLAIM!r}")
    esiti = {}
    for nome, fonte, atteso in FONTI:
        try:
            riusati = valori_riusati_da_altro_contesto(CLAIM, fonte)
        except Exception as e:  # noqa: BLE001
            print(f"     {nome:<38} ECCEZIONE {type(e).__name__}: {e}")
            continue
        esiti[nome] = bool(riusati)
        marchio = "SEGNALA" if riusati else "tace   "
        print(f"     {nome:<38} {marchio}   (atteso: {atteso})")
        for r in riusati[:2]:
            print(f"        {r.valore:g} qui «{r.nel_claim}», nella fonte «{r.nella_fonte}»")

    print("\n  -- CONTROLLO (2): e' la POSIZIONE dell'etichetta?")
    a = esiti.get("A tabella allineata (il caso VERO)")
    b = esiti.get("B etichetta a DESTRA del numero")
    c = esiti.get("C prosa, etichetta a destra")
    print(f"     A tabella={a}   B destra={b}   C prosa={c}")
    if a and not b:
        print("     RETTA - la stessa informazione, spostata a destra del numero,")
        print("     non viene piu' segnalata. Il layer legge il vicinato a DESTRA,")
        print("     e su una tabella allineata a destra non c'e' l'etichetta.")
    elif a and b:
        print("     CADUTA - segnala anche con l'etichetta a destra: non e' il")
        print("     lato. La causa e' un'altra e questo banco non la trova.")
    elif not a:
        print("     NON RIPRODOTTO - sul caso vero il layer tace da qui, mentre")
        print("     nella ricevuta delle 23:03 aveva parlato. Cambia qualcosa")
        print("     fra questa chiamata e la porta del prodotto: dirlo prima di")
        print("     concludere.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
