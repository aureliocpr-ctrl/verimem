r"""`L1.20` ferma un claim VERO, e il perche' era gia' nella ricevuta.

Nella cella `W5-2` avevo misurato **che** `L1.20` fa cadere un claim vero, e
dichiarato di non sapere **perche'**. Non serviva un banco nuovo: serviva
leggere il warning INTERO invece del solo `w["layer"]`.

    'La merce e' arrivata integra'   downgrade g=98.9  cos 0.863  delta 0.053
         matched_exemplar: 'this is ready to ship, fully validated'
    'The goods arrived undamaged'     downgrade g=99.4  cos 0.846  delta 0.057
         matched_exemplar: 'die gesamte Testsuite lauft ohne Fehler durch'
    CONTROLLO 'La spedizione non ha subito danni'  -> persist g=95.8, L1.20 MUTO
    CONTROLLO 'Ho verificato che tutto funziona'   -> downgrade g=42.6, cos 0.905, delta 0.075

⇒ **E' una COLLISIONE DI DOMINIO, non un meccanismo rotto.** Gli exemplars di
`L1.20` usano la metafora logistica del software — *«ready to SHIP, fully
validated»* — e un claim di logistica **letterale** ci cade dentro a `cos 0.863`.
Il caso inglese e' piu' netto ancora: un claim di spedizione matcha un exemplar
**tedesco** che parla di una test suite.
⇒ **Il detector funziona sul suo dominio**: il controllo positivo (un self-claim
vero) esce a `0.905` con `delta 0.075`, il piu' alto dei quattro.
⇒ **La prova per differenza**: *«La spedizione non ha subito danni»* - stesso
fatto, stessa fonte, altre parole - **passa**, e `L1.20` tace. Cambia la
formulazione, non il contenuto.

DOVE GUARDEREI LA CURA, **non misurata e quindi non proposta**: il `delta`
separa gia' (0.053 e 0.057 contro 0.075), ma **con UN solo vero positivo non si
tara una soglia**; oppure togliere le metafore logistiche dagli exemplars, che
e' piu' chirurgico. ⚠️ **Entrambe vanno misurate sui DUE versi**: alzare il
delta fa passare self-claim veri, che e' il difetto opposto - quello che @ws8
ha curato il 28/08 (`54bb9d73`, `L1.20` che taceva).

🔑 **La lezione, e vale oltre questo caso: la ricevuta sapeva gia' il perche'.**
`matched_exemplar`, `score` e `delta` c'erano; io stampavo solo `w["layer"]` e
ho misurato **che cosa** succede per un'ora invece di leggere **perche'**.

REGIME: build corrente · SHA dichiarato nell'esecuzione · store TEMPORANEO
rimosso da un `trap` · `ground_write=True`.
⚖️ PUNTI DEBOLI: due falsi positivi e **un solo** vero positivo - i tre delta
non bastano a tarare niente, servono le due popolazioni intere. E gli exemplars
non li ho letti tutti: so quale ha fatto match, non quanti altri collidono.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-L120-collisione-di-dominio.py <dir-temp>
"""
import os, sys, json
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

CASI = [
 ("il VERO che cade (IT)", "La merce e' arrivata integra.",
  "La merce e' stata spedita il 12 aprile ed e' arrivata integra."),
 ("il VERO che cade (EN)", "The goods arrived undamaged.",
  "The goods were shipped on April 12th and arrived undamaged."),
 ("controllo: stesso fatto, altre parole", "La spedizione non ha subito danni.",
  "La merce e' stata spedita il 12 aprile ed e' arrivata integra."),
 ("controllo: un self-claim VERO (deve cadere)", "Ho verificato che tutto funziona correttamente.",
  "Il modulo e' stato modificato per gestire il caso limite."),
]
for nome, claim, fonte in CASI:
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None, agent=None,
                            source=fonte, grounding_llm=None, ground_write=True)
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    print("\n--- %s -> %s (g=%.1f)" % (nome, az, getattr(r, "grounding_score", 0) or 0))
    print("    claim: %s" % claim)
    for w in (getattr(r, "warnings", None) or []):
        if isinstance(w, dict) and w.get("layer") == "L1.20":
            for k, v in w.items():
                print("      %-14s %s" % (k, str(v)[:150]))
