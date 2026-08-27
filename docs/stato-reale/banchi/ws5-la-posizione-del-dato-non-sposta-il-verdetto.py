# -*- coding: utf-8 -*-
r"""La POSIZIONE del dato non sposta il verdetto sui FALSI — ma abbassa il punteggio.

    ancora INIZIO  (247 parole)  VERO=persist 100.0  ricalco24=downgrade 0.2  CONTROLLO61=downgrade 36.5
    ancora CENTRO  (247 parole)  VERO=persist 100.0  ricalco24=downgrade 0.2  CONTROLLO61=downgrade 36.5
    ancora FINE    (247 parole)  VERO=persist 100.0  ricalco24=downgrade 0.7  CONTROLLO61=downgrade 16.1

NASCE DA UN'OSSERVAZIONE DI @ws2 (27/08 20:46): «la POSIZIONE del dato dentro la
fonte decide se un fatto vero entra o viene quarantinato». Minacciava un confondente
**non dichiarato** nei banchi Q2: li' la fonte era troncata ATTORNO all'ancora, quindi
il valore vero stava **sempre al centro**. Preso come test contro i miei stessi
risultati.

⇒ IL CONFONDENTE NON C'E'. **INIZIO e CENTRO sono identici**; in FINE il punteggio si
muove **verso il basso** (36.5 → 16.1), cioe' nella direzione piu' sicura. Il verdetto
non cambia mai, e i controlli tengono: il VERO passa a 100.0 in tutte e tre le celle.
⇒ Le conclusioni di `ws5-Q2-la-ripetizione-non-e-la-variabile.py` reggono anche
variando la posizione.

🔑 MA LA COSA CHE VALE E' PERCHE' IL SUO RISULTATO E IL MIO NON SI CONTRADDICONO:
**misuriamo le due popolazioni opposte.**
  · @ws2: un fatto **VERO** che viene quarantinato (falso positivo). Li' il punteggio
    deve **raggiungere** una soglia, e tutto cio' che lo abbassa puo' farlo cadere sotto.
  · qui: un fatto **FALSO** che deve essere bloccato (falso negativo). Il claim e'
    **contraddetto** dalla fonte e `L4-negazione` scatta ovunque essa stia.
⇒ **La posizione conta dove il punteggio deve SALIRE, non dove deve scendere.**

⚖️ E LA RICADUTA PRATICA E' NEL VERSO GIUSTO PER PREOCCUPARSI: il punteggio scende
quando il dato e' in fondo (36.5 → 16.1), coerente col verso misurato da @ws2. ⇒ **Su
un contratto lungo le clausole FINALI sono le piu' esposte al suo difetto** — e penali,
termini e firme stanno in fondo.

⚠️ PUNTO DEBOLE: tre celle, tre claim, una sola fonte costruita per avere un'ancora
spostabile. E **misura la mia popolazione, non la sua**: per rispondere alla domanda di
@ws2 servono claim VERI che possano scendere sotto soglia, e questo banco ha gli
strumenti puntati sull'altro lato.

REGIME: build `f5dedf34` · python 3.13.12 · store temporaneo · `run_validation_gate`,
la porta che usa la CLI (`cli.py:1867`) · fonte 247 parole, identica nelle tre celle.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-posizione-del-dato-non-sposta-il-verdetto.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

ANCORA = ("In the case of a personal data breach, the controller shall, where feasible, not later "
 "than 72 hours after having become aware of it, notify the personal data breach to the "
 "supervisory authority. ")
RIEMPIMENTO = ("The processor shall notify the controller without undue delay after becoming aware "
 "of a personal data breach. The notification shall describe the nature of the breach, "
 "communicate the name and contact details of the data protection officer, describe the likely "
 "consequences, and describe the measures taken by the controller. The controller shall document "
 "any personal data breaches, comprising the facts relating to the breach, its effects and the "
 "remedial action taken. That documentation shall enable the supervisory authority to verify "
 "compliance with this Article. Where it is not possible to provide the information at the same "
 "time, it may be provided in phases without undue further delay. ")

FONTI = [("INIZIO",  ANCORA + RIEMPIMENTO + RIEMPIMENTO),
         ("CENTRO",  RIEMPIMENTO + ANCORA + RIEMPIMENTO),
         ("FINE",    RIEMPIMENTO + RIEMPIMENTO + ANCORA)]
CLAIM = [("VERO 72",      "The controller shall notify the personal data breach to the supervisory authority not later than 72 hours after having become aware of it."),
         ("ricalco 24",   "The controller shall notify the personal data breach to the supervisory authority not later than 24 hours after having become aware of it."),
         ("CONTROLLO 61", "The controller shall notify the personal data breach to the supervisory authority not later than 61 hours after having become aware of it.")]
print("")
for eti_f, src in FONTI:
    out = []
    for eti_c, claim in CLAIM:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=src, grounding_llm=None, ground_write=True)
        g = getattr(r, "grounding_score", None)
        out.append("%-9s=%-9s g=%5s" % (eti_c.split()[-1][:5], getattr(r, "action", "?")[:9],
                   ("%.1f" % g) if isinstance(g, (int, float)) else "-"))
    print("   ancora %-7s (%3d parole)  %s" % (eti_f, len(src.split()), "  ".join(out)))
