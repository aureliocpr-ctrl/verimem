# -*- coding: utf-8 -*-
"""IL SECONDO MECCANISMO DI @ws6, e il controllo che gli manca.

@ws6 (28/08 22:50, canale) ha isolato che la parola «nota» in una FONTE rende
`L4.1` cieco a tutti i numeri di quella fonte, e ha dichiarato il limite:

    «Nota: la soglia 0.40 produce un cluster solo.» ........... ACCECATO
    «Si veda la soglia 0.40 che produce un cluster solo.» ..... ACCECATO
    ⇒ «Il secondo caso non contiene «nota» e acceca lo stesso. C'e' almeno un
       secondo meccanismo che NON ho isolato.»

⚠️ **Il controllo che chiude la domanda non c'e' nel suo banco**: la STESSA
frase SENZA «Si veda». Se anche quella acceca, «Si veda» non c'entra e la causa
e' la forma discorsiva; se invece trova, «Si veda» e' un secondo marcatore.
Costa zero e cambia la diagnosi.

Aggiungo il livello che manca: `L4.1` legge i due lati con DUE modalita'
(`valore_non_nella_fonte.py:205`: «*il claim con `extract_quantities(p)`, la
fonte con `extract_quantities(s, come_fonte=True)`*»), quindi misuro anche
COSA ESTRAE la fonte, non solo il verdetto. Un verdetto dice CHE e' cieco;
l'estrazione dice DOVE.

CONTROLLI CHE POSSONO FALLIRE:
 (1) la riproduzione del reperto di @ws6: se sulla mia macchina «nota» NON
     acceca, il reperto non si riproduce e il mio banco non ha oggetto. Lo dico.
 (2) il controllo positivo: la fonte nuda DEVE trovare il valore. Se non lo
     trova nemmeno lei, sto misurando un guasto mio e non il difetto.
 (3) se la frase discorsiva SENZA marcatore acceca lo stesso, la mia ipotesi
     «e' un secondo marcatore» CADE e lo scrivo.

    python -u docs/stato-reale/banchi/chi-acceca-L4-1-la-parola-o-la-forma-della-frase.py
"""

from __future__ import annotations

import sys

CLAIM = "Con soglia 0.40 i cluster sono 1."
RIGA = "    0.40         1         431           0"

# nome -> (fonte, cosa mi aspetto secondo il reperto di ws6)
CASI = [
    ("A nuda (controllo positivo)", RIGA, "TROVA"),
    ("B nuda + 'nota' in testa", "  nota\n" + RIGA, "acceca (reperto ws6)"),
    ("C discorsiva con 'Nota:'",
     "Nota: la soglia 0.40 produce un cluster solo.", "acceca (reperto ws6)"),
    ("D discorsiva con 'Si veda'",
     "Si veda la soglia 0.40 che produce un cluster solo.", "acceca (reperto ws6)"),
    # ---- IL CONTROLLO CHE MANCA A ws6: la stessa D senza il marcatore ----
    ("E discorsiva NUDA (il controllo mancante)",
     "La soglia 0.40 produce un cluster solo.", "?"),
    # ---- e le due varianti che separano la parola dalla forma ----
    ("F discorsiva con 'Vedi'",
     "Vedi la soglia 0.40 che produce un cluster solo.", "?"),
    ("G discorsiva con parola neutra",
     "Alfa la soglia 0.40 che produce un cluster solo.", "?"),
]


def main() -> int:
    try:
        from verimem import valore_non_nella_fonte as vnf
        from verimem.quantity_match import extract_quantities
        from verimem.valore_non_nella_fonte import valori_non_nella_fonte
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1
    print(f"  codice sotto misura: {vnf.__file__}")
    print(f"  claim: {CLAIM!r}")

    esiti = {}
    print("\n  == IL VERDETTO (cio' che vede il prodotto) e L'ESTRAZIONE (dove)")
    for nome, fonte, atteso in CASI:
        try:
            assenti = valori_non_nella_fonte(CLAIM, fonte)
        except Exception as e:  # noqa: BLE001
            print(f"     {nome:<40} ECCEZIONE {type(e).__name__}: {e}")
            continue
        valori = [getattr(a, "valore", a) for a in assenti]
        cieco = any(abs(float(getattr(a, "valore", 0.0)) - 0.40) < 1e-9
                    for a in assenti)
        try:
            q_fonte = extract_quantities(fonte, come_fonte=True)
        except TypeError:
            q_fonte = extract_quantities(fonte)
        numeri_fonte = sorted({v for _u, v in q_fonte})
        esiti[nome] = cieco
        marchio = "ACCECATO" if cieco else "trova   "
        print(f"     {nome:<40} {marchio}  assenti={valori}")
        print(f"       {'':<38} fonte estrae -> {numeri_fonte}")
        print(f"       {'':<38} atteso da ws6: {atteso}")

    print("\n  -- CONTROLLO (2): la fonte nuda DEVE trovare il valore")
    if esiti.get("A nuda (controllo positivo)", True):
        print("     CADUTO - nemmeno la fonte nuda trova 0.40: sto misurando un")
        print("     guasto mio, non il difetto di @ws6. Il resto non vale.")
        return 1
    print("     retto - la fonte nuda trova 0.40")

    print("\n  -- CONTROLLO (1): il reperto di @ws6 si riproduce?")
    b = esiti.get("B nuda + 'nota' in testa")
    c = esiti.get("C discorsiva con 'Nota:'")
    if b and c:
        print("     SI - 'nota' acceca in entrambe le forme, come dichiarato.")
    else:
        print(f"     NO - B={b} C={c}: sulla mia macchina il reperto NON si"
              " riproduce come scritto.")

    print("\n  -- CONTROLLO (3): 'Si veda' e' un marcatore, o e' la FORMA?")
    d = esiti.get("D discorsiva con 'Si veda'")
    e = esiti.get("E discorsiva NUDA (il controllo mancante)")
    f = esiti.get("F discorsiva con 'Vedi'")
    g = esiti.get("G discorsiva con parola neutra")
    print(f"     D 'Si veda'={d}   E nuda={e}   F 'Vedi'={f}   G 'Alfa'={g}")
    if d and e:
        print("     ⇒ LA MIA IPOTESI CADE: acceca anche SENZA 'Si veda'.")
        print("       Il secondo meccanismo NON e' un marcatore lessicale: e' la")
        print("       forma della frase. La riga di @ws6 su 'Si veda' attribuisce")
        print("       a una parola un effetto che la parola non ha.")
    elif d and not e:
        print("     ⇒ 'Si veda' E' un secondo marcatore: la stessa frase senza")
        print("       di esso trova il valore. @ws6 aveva ragione a sospettarlo.")
        if g:
            print("       ⚠️ MA acceca anche con una parola neutra ('Alfa'):"
                  " allora non e' il LESSICO, e' la POSIZIONE.")
    elif not d:
        print("     ⇒ D non acceca da me: il caso di @ws6 non si riproduce e la")
        print("       domanda sul secondo meccanismo va riaperta sul suo banco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
