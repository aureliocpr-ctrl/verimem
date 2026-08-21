"""Banco: la PRIMA PAROLA della frase decide se due fatti si mangiano.

Perche' e' uno script e non un test: la meta' [C] scrive davvero nel prodotto e
sotto pytest `tests/conftest.py` sostituisce l'embedder con uno stub — il ramo
semantico deciderebbe con un righello finto (lezione di ws5, commit c1d94829).
Le meta' [A] e [B] sono lessicali e stanno anche in
`tests/test_aperture_e_lato_solo.py`, dove restano rosse se la cura si perde.

    python docs/stato-reale/banchi/ws3-aperture-e-lato-solo.py

Stampa da dove importa `verimem`: senza, misura un altro albero senza dirlo.
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

import verimem.anti_confab_gate as g  # noqa: E402

print("importa verimem da : %s" % g.__file__)
print("parole d'apertura  : %d" % len(g._parole_vuote_iniziali()))
print()

_f = lambda p: types.SimpleNamespace(proposition=p)  # noqa: E731
CODA = " la cella ha stampato 1 failed"

# [A] due record DIVERSI, cambia solo la parola d'apertura -> devono coesistere
APERTURE = [("IT", "Su"), ("IT", "In"), ("IT", "Di"), ("IT", "Da"), ("IT", "Tra"),
            ("IT", "Nel"), ("IT", "Il run"), ("EN", "On"), ("EN", "At"),
            ("EN", "By"), ("EN", "To"), ("EN", "Of"), ("EN", "The run"), ("EN", "For")]

# [B] un lato nomina il record, l'altro no -> in dubbio non si ritira
LATO_SOLO = [
    ("La cella stampa 1 failed e 11767 passed.",
     "Su b7bc7b77 la cella py3.13 stampa 8019 warnings."),
    ("Sotto pytest la domanda in olandese ottiene score 0.7006.",
     "Fuori da pytest la domanda in olandese ottiene score 0.8509."),
    ("Nel corpus i fatti live non quarantinati sono 4304.",
     "Il tool hippo_extract_entities sul testo di Aurelio rende 3 entita."),
]

# [C] PRESIDIO: stesso record, valore che cambia -> DEVE continuare a ritirare
PRESIDIO = [
    ("Su 42bb3839 la cella ha stampato 1 failed",
     "Su 42bb3839 la cella ha stampato 3 failed"),
    ("On 42bb3839 the cell printed 1 failed",
     "On 42bb3839 the cell printed 3 failed"),
    ("Su 42bb3839 la versione e' 2.3.1", "Su 42bb3839 la versione e' 4.0.0"),
]

falliti = 0

print("[A] RECORD DIVERSI, cambia solo l'apertura — attesa: coesistono")
for ling, ap in APERTURE:
    esito = g._entita_diverse(_f(ap + " 42bb3839" + CODA), _f(ap + " b7bc7b77" + CODA))
    falliti += not esito
    print("    %-3s %-9s coesistono=%-5s %s" % (ling, ap, esito, "ok" if esito else "ROTTA"))

print()
print("[B] UN LATO SOLO nomina il record — attesa: non si ritira")
for pa, pb in LATO_SOLO:
    esito = g._entita_diverse(_f(pa), _f(pb))
    falliti += not esito
    print("    coesistono=%-5s %s  %s" % (esito, "ok" if esito else "ROTTA", pa[:52]))

print()
print("[C] PRESIDIO — stesso record, valore cambiato — attesa: NON coesistono")
for pa, pb in PRESIDIO:
    esito = g._entita_diverse(_f(pa), _f(pb))
    falliti += bool(esito)
    print("    coesistono=%-5s %s  %s" % (esito, "ok" if not esito else "SPENTA", pa[:52]))

print()
print("PORTATA sul corpus di produzione (1933 supersessioni reali, A/B su due")
print("alberi, la funzione vera in entrambi):")
print("    non avvengono piu'    27  (1.4%)   di cui entrambi >=90: 26")
print("    iniziano ad avvenire   1  (0.1%)   di cui entrambi >=90:  0")
print("    invariate           1905 (98.6%)")
print()
print("FALLITI: %d" % falliti)
sys.exit(1 if falliti else 0)
