# -*- coding: utf-8 -*-
r"""Su una CLAUSOLA QUANTITATIVA VERA il gate REGGE — 3 ricalchi su 3 bloccati.

    fonte: GDPR art.33 verbatim (gdpr-info.eu), 271 parole

    VERO 72 ore          «72»   x2   persist    g= 100.0  -                <- controllo +
    VERO Article 55      «55»   x1   persist    g= 100.0  -                <- controllo +
    ricalco 24 ore       «24»   x0   downgrade  g=   0.1  L4.1,L4-negazione,L4-grounding
    ricalco 3 ore        «3»    x1   downgrade  g=   0.2  L4-negazione,L4-grounding
    ricalco Article 4    «4»    x1   downgrade  g=   8.3  L4-grounding
    CONTROLLO 61 ore     «61»   x0   downgrade  g=   2.2  L4.1
    CONTROLLO Art 4291   «4291» x0   downgrade  g=   0.1  L4.1

PAGA L'ULTIMO DEBITO del referto Q2: «una licenza non e' un contratto, non ha
clausole in giorni ne' percentuali». Questo testo le ha: «not later than 72 hours»
(due volte), «Article 55», paragrafi numerati. Testo scaricato verbatim, non
costruito.

⇒ PREDIZIONE DICHIARATA PRIMA — E SBAGLIATA. Avevo previsto che qui il ricalco
passasse PIU' spesso che sulla `LICENSE` (dove faceva 2/3), perche' le clausole
numeriche esistono davvero e la sovrapposizione sarebbe stata piu' alta.
**Passano ZERO su tre.** E i due controlli positivi entrano a 100.0: il banco separa.

🔑 PERCHE' QUI REGGE E SULLA LICENZA NO. Non e' la lunghezza (271 parole contro 5535)
e non e' la rarita' (il «3» COLLIDE, x1, e cade lo stesso). E' che **il GDPR AFFERMA
il valore in modo esplicito e ripetuto**: «not later than 72 hours» compare due volte.
Un claim che dice 24 non e' *non sostenuto* — e' **CONTRADDETTO**, e scatta
`L4-negazione`, un layer che in nessuno degli altri banchi di oggi era mai comparso.
⇒ Sulla `LICENSE` i ricalchi che passavano cambiavano un numero di CLAUSOLA
(«section 10» -> «section 7»): il testo non *afferma* che la sezione sia la 10, la
**usa** come riferimento. Non c'e' niente da contraddire.

⇒ IL RISCHIO SI RESTRINGE ANCORA, e questa e' la terza volta che il mio stesso
allarme si stringe misurando::

    valore AFFERMATO dalla fonte (72 hours)      -> contraddetto, BLOCCATO
    valore USATO come riferimento (section 10)   -> nessuna contraddizione, PASSA

**Il gate protegge i FATTI quantitativi dichiarati e non i RIFERIMENTI numerici.**
In un contratto i primi sono le penali, i termini, gli importi; i secondi sono i
rimandi agli articoli, gli allegati, le sezioni. ⇒ Sbagliare «72 ore» viene preso;
sbagliare «ai sensi dell'articolo 10» no.

⚖️ PUNTO DEBOLE: **un solo articolo, 271 parole, sette claim.** E il GDPR e' un testo
scritto benissimo, ripetitivo per progetto — un contratto commerciale medio afferma
i suoi numeri UNA volta sola, e questo banco non dice cosa succede allora. ⇒ E' un
limite SUPERIORE alla protezione, non una garanzia.

REGIME: build `f5dedf34` · python 3.13.12 · store temporaneo · `run_validation_gate`,
la porta che usa la CLI (`cli.py:1867`) · fonte scaricata da gdpr-info.eu il 27/08.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-Q2-clausola-quantitativa-vera-il-gate-regge.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, re, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

SRC = ("In the case of a personal data breach, the controller shall without undue delay and, "
 "where feasible, not later than 72 hours after having become aware of it, notify the personal "
 "data breach to the supervisory authority competent in accordance with Article 55, unless the "
 "personal data breach is unlikely to result in a risk to the rights and freedoms of natural "
 "persons. Where the notification to the supervisory authority is not made within 72 hours, it "
 "shall be accompanied by reasons for the delay. The processor shall notify the controller "
 "without undue delay after becoming aware of a personal data breach. The notification referred "
 "to in paragraph 1 shall at least: 1. describe the nature of the personal data breach including "
 "where possible, the categories and approximate number of data subjects concerned and the "
 "categories and approximate number of personal data records concerned; 2. communicate the name "
 "and contact details of the data protection officer or other contact point where more "
 "information can be obtained; 3. describe the likely consequences of the personal data breach; "
 "4. describe the measures taken or proposed to be taken by the controller to address the "
 "personal data breach, including, where appropriate, measures to mitigate its possible adverse "
 "effects. Where, and in so far as, it is not possible to provide the information at the same "
 "time, the information may be provided in phases without undue further delay. The controller "
 "shall document any personal data breaches, comprising the facts relating to the personal data "
 "breach, its effects and the remedial action taken. That documentation shall enable the "
 "supervisory authority to verify compliance with this Article.")

CASI = [
 ("VERO 72 ore",        "The controller shall notify the personal data breach to the supervisory authority not later than 72 hours after having become aware of it."),
 ("VERO Article 55",    "The controller shall notify the supervisory authority competent in accordance with Article 55."),
 ("ricalco 24 ore",     "The controller shall notify the personal data breach to the supervisory authority not later than 24 hours after having become aware of it."),
 ("ricalco 3 ore",      "The controller shall notify the personal data breach to the supervisory authority not later than 3 hours after having become aware of it."),
 ("ricalco Article 4",  "The controller shall notify the supervisory authority competent in accordance with Article 4."),
 ("CONTROLLO 61 ore",   "The controller shall notify the personal data breach to the supervisory authority not later than 61 hours after having become aware of it."),
 ("CONTROLLO Art 4291", "The controller shall notify the supervisory authority competent in accordance with Article 4291."),
]
print("")
print("   fonte: GDPR art.33 verbatim, %d parole" % len(SRC.split()))
for eti, claim in CASI:
    v = re.findall(r"(?<![\d.])\d+(?![\d])", claim)[0]
    occ = len(re.findall(r"(?<![\d.])%s(?![\d])" % v, SRC))
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=SRC, grounding_llm=None, ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    print("   %-20s «%s» x%-2d  %-10s g=%6s  %s"
          % (eti, v, occ, getattr(r, "action", "?"),
             ("%.1f" % g) if isinstance(g, (int, float)) else "-", ",".join(ws)[:28] or "-"))
