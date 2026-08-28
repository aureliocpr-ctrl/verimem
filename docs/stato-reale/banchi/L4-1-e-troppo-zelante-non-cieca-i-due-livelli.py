# -*- coding: utf-8 -*-
"""A QUALE LIVELLO GIRA LA POTATURA? Il verdetto cambia col righello.

quantity_match.py:1133-1134 applica gli span al CLAIM:
    _date = _spans_delle_date(claim); _riferimenti = _spans_dei_riferimenti(claim)
Ma il difetto di @ws6 e' sulla FONTE. Prima di dire che un commento e' falso
devo misurare dove il prodotto chiama, e DICHIARARE il livello.

Tre livelli, stessa coppia:
  L1  extract_quantities(testo, come_fonte=True)   <- l'estrattore
  L2  valori_non_nella_fonte(claim, source)        <- il layer L4.1
CONTROLLO: se i due livelli danno verdetti diversi, cito il livello o non cito.
"""
from verimem.quantity_match import extract_quantities
from verimem.valore_non_nella_fonte import valori_non_nella_fonte


def q(t, fonte=True):
    try:
        return sorted({v for _u, v in extract_quantities(t, come_fonte=fonte)})
    except TypeError:
        return sorted({v for _u, v in extract_quantities(t)})


COPPIE = [
    # (nome, claim, source)
    ("l'esempio DEL COMMENTO",
     "Il comma 2 prevede 5 giorni.", "Il comma 2 prevede 5 giorni di termine."),
    ("il commento, valore INVENTATO",
     "Il comma 2 prevede 9 giorni.", "Il comma 2 prevede 5 giorni di termine."),
    ("nota + decimale (caso ws6)",
     "Con soglia 0.40 i cluster sono 1.", "  nota\n    0.40         1"),
    ("nota + decimale, valore INVENTATO",
     "Con soglia 0.99 i cluster sono 1.", "  nota\n    0.40         1"),
]

print("  == L1 l'estrattore, sui due lati")
for nome, claim, src in COPPIE:
    print(f"     {nome}")
    print(f"       claim  come_claim={q(claim, False)}   come_fonte={q(claim, True)}")
    print(f"       source come_fonte={q(src, True)}")

print("\n  == L2 il layer L4.1 (la porta che il prodotto chiama)")
for nome, claim, src in COPPIE:
    assenti = valori_non_nella_fonte(claim, src)
    vals = [float(getattr(a, "valore", 0.0)) for a in assenti]
    print(f"     {nome:<36} assenti={vals}")

print("\n  -- CONTROLLO: i due livelli concordano?")
c_vero = valori_non_nella_fonte("Il comma 2 prevede 5 giorni.",
                                "Il comma 2 prevede 5 giorni di termine.")
c_falso = valori_non_nella_fonte("Il comma 2 prevede 9 giorni.",
                                 "Il comma 2 prevede 5 giorni di termine.")
print(f"     comma, claim VERO  -> assenti={[float(getattr(a,'valore',0)) for a in c_vero]}"
      "   (deve essere vuoto)")
print(f"     comma, claim FALSO -> assenti={[float(getattr(a,'valore',0)) for a in c_falso]}"
      "   (deve contenere 9)")
if not c_vero and any(abs(float(getattr(a, "valore", 0)) - 9.0) < 1e-9 for a in c_falso):
    print("     RETTO alla PORTA - sul caso del commento il layer fa la cosa giusta")
    print("     nei due versi. Qualunque cosa dica l'estrattore piu' sotto.")
else:
    print("     ATTENZIONE - alla porta il comportamento NON e' quello atteso:")
    print("     leggi le due righe sopra prima di citare.")
