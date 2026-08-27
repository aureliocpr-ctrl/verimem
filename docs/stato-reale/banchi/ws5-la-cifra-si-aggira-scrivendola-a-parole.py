# -*- coding: utf-8 -*-
r"""L'unico punto forte del gate si aggira scrivendo il numero A PAROLE: 0/6 contro 6/6.

    CIFRA    ammessi 0/6   L4.1 ha parlato su 6/6
    LETTERE  ammessi 6/6   L4.1 ha parlato su 0/6

    EN   CIFRA=bloc   LETTERE=AMMESSO (senza L4.1)
    IT   CIFRA=bloc   LETTERE=AMMESSO (senza L4.1)
    ZH   CIFRA=bloc   LETTERE=AMMESSO (senza L4.1)      340箱 -> 三百四十箱
    JA   CIFRA=bloc   LETTERE=AMMESSO (senza L4.1)      340個 -> 三百四十個

Separazione totale, quattro scritture su quattro, ideogrammi compresi. E `L4.1`
non parla MAI sulla forma in lettere: non e' che parla e si sbaglia — non vede
proprio che c'e' un numero.

DA DOVE VIENE, e la catena conta perche' nessuno dei tre pezzi da solo lo diceva:
  · @ws3 ha misurato che il dettaglio NUMERICO e' fermato 18/18 da `L4.1` mentre
    il non numerico sfugge 16/18 ⇒ «l'asse non e' la lingua, e' la cifra».
  · io ho verificato che il TRAINO non scalfisce quel 18/18
    (`ws5-il-traino-contro-la-cifra.py`): l'unico strato che regge, regge davvero.
  · restava una sola domanda: e se il numero non e' scritto in cifra?

⚠️ NON E' UNA SCOPERTA NUOVA, ed e' O1 ad avermelo detto PRIMA di misurare: in
memoria c'erano gia' `lessons/verimem/ab-l41-numero-in-lettere-0` e `-1` — «6» in
cifra esce quarantined, «SEI» in lettere esce model_claim con grounding 99.98.
Quello e' un A/B su UN numero in UNA lingua. Questo banco dice che **e'
sistematico**: sei casi reali, quattro scritture, separazione 0/6 vs 6/6.

⇒ CIO' CHE CAMBIA. Con il solo A/B si poteva dire «caso limite, una parola
particolare». Con 6/6 su quattro scritture no: **la superficie protetta non e' «i
numeri», sono «i numeri scritti in cifra»**, e la riscrittura che la aggira e'
quella che un LLM produce da solo quando parla in prosa. In italiano
«trecentoquaranta colli» e' PIU' naturale di «340 colli» in una frase discorsiva.
⇒ Non serve un attaccante: **basta scrivere normalmente.**

⇒ E CHIUDE IL QUADRO DEI DUE STRATI, in peggio::

    `L4.1` sulle CIFRE     regge 18/18, immune al traino e alla scrittura...
                           ...ma solo se il numero e' in cifra: 6/6 lo aggira
    punteggio SEMANTICO    comprabile in QUATTRO modi (ripetere la fonte,
                           ricombinare i suoi token, il traino, il contorno neutro)

Il gate NON ha un punto debole e un punto forte. Ha un punto forte **con una porta
accanto**, e dietro la porta non c'e' un secondo strato: c'e' il punteggio, che si
compra.

⚠️ LIMITE DICHIARATO: sei casi, quattro scritture, numeri interi «tondi» (340, 27,
12). NON ho provato decimali a parole («tre virgola cinque»), ne' forme miste
(«340 mila»), ne' AR/HI/KO. Il numero 6/6 e' netto ma la popolazione e' piccola:
serve estenderlo prima di scriverlo in vetrina.
⛔ NESSUNA CURA PROPOSTA. Riconoscere i numeri a parole in N lingue e' un problema
aperto, non una riga di regex, e una cura che non so misurare non si consegna.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-cifra-si-aggira-scrivendola-a-parole.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA: scrive in HIPPO_DATA_DIR, mai lo store principale.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

#: (lingua, fonte, claim-CIFRA, claim-LETTERE)
CASI = [
 ("EN", "Logistics note: the shipment was delivered to the Bari depot.",
        "340 parcels were delivered to the Bari depot.",
        "Three hundred and forty parcels were delivered to the Bari depot."),
 ("EN", "Report: the Verona branch hired new staff.",
        "The Verona branch hired 27 people.",
        "The Verona branch hired twenty-seven people."),
 ("IT", "Nota logistica: la merce e' stata consegnata al deposito di Bari.",
        "340 colli sono stati consegnati al deposito di Bari.",
        "Trecentoquaranta colli sono stati consegnati al deposito di Bari."),
 ("IT", "Verbale: il consiglio ha approvato il bilancio.",
        "Il consiglio ha approvato il bilancio con 12 voti favorevoli.",
        "Il consiglio ha approvato il bilancio con dodici voti favorevoli."),
 ("ZH", "物流记录：货物已送达巴里仓库。",
        "340箱货物已送达巴里仓库。",
        "三百四十箱货物已送达巴里仓库。"),
 ("JA", "物流記録：荷物はバーリ倉庫に配達されました。",
        "340個の荷物がバーリ倉庫に配達されました。",
        "三百四十個の荷物がバーリ倉庫に配達されました。"),
]

def prova(claim, src):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=src, grounding_llm=None, ground_write=True)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    return (getattr(r, "action", "?") == "persist",
            any(str(w).startswith("L4.1") for w in ws))

amm = {"CIFRA": 0, "LETTERE": 0}
l41 = {"CIFRA": 0, "LETTERE": 0}
print("")
for lg, src, c_cifra, c_lettere in CASI:
    out = []
    for eti, claim in (("CIFRA", c_cifra), ("LETTERE", c_lettere)):
        ok, ha41 = prova(claim, src)
        amm[eti] += int(ok); l41[eti] += int(ha41)
        out.append("%s=%s%s" % (eti, "AMMESSO" if ok else "bloc", "" if ha41 else " (senza L4.1)"))
    print("   %-3s  %s" % (lg, "   ".join(out)))
print("")
n = len(CASI)
for eti in ("CIFRA", "LETTERE"):
    print("   %-8s ammessi %d/%d   L4.1 ha parlato su %d/%d" % (eti, amm[eti], n, l41[eti], n))
