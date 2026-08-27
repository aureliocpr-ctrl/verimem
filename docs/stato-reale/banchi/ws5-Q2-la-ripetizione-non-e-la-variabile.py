# -*- coding: utf-8 -*-
r"""La RIPETIZIONE non e' la variabile — ma senza, il margine si assottiglia 20 volte.

    CON ripetizione («72» x2, 161 parole)     SENZA ripetizione («72» x1, 139 parole)
      VERO 72       persist    g= 100.0        VERO 72       persist    g= 100.0
      ricalco 24    downgrade  g=   0.1        ricalco 24    downgrade  g=   0.2
      ricalco 48    downgrade  g=   0.2        ricalco 48    downgrade  g=   0.2
      CONTROLLO 61  downgrade  g=   2.8        CONTROLLO 61  downgrade  g=  64.9  <-

Paga l'ultimo debito del referto Q2: «il GDPR e' ripetitivo per progetto, un
contratto commerciale afferma i suoi numeri UNA VOLTA SOLA — questo banco non dice
cosa succede allora». A/B a testo identico, tolta la seconda occorrenza di
«72 hours» (la frase sui motivi del ritardo).

⇒ PREDIZIONE DICHIARATA PRIMA E SBAGLIATA (la quinta di oggi): avevo previsto che
senza ripetizione il ricalco passasse. **Cade identico** — 0.2 contro 0.1. **UNA sola
affermazione basta a far scattare `L4-negazione`.** La protezione sulle clausole
affermate non dipende dalla ridondanza del testo.

⚠️ MA IL CONTROLLO RIVELA LA FRAGILITA', ed e' il motivo per cui questo banco vale::

    CONTROLLO 61   con ripetizione:  g= 2.8   layers L4.1,L4-negazione,L4-grounding
    CONTROLLO 61   senza:            g=64.9   layers L4.1,**L4-review**

Il valore 61 — assente dalla fonte, e per questo il controllo — passa da 2.8 a
**64.9**: venti volte. E cambia lama: `L4-negazione` sparisce, resta `L4-review`.
Il verdetto tiene solo perche' `L4.1` lo vede (61 non e' nel testo). ⇒ **Sul caso in
cui `L4.1` e' cieco — numero comune, a parole, o unita' diversa — quel 64.9 non
avrebbe nessuno sotto.**

🔑 LA LETTURA ONESTA: la ripetizione non decide il VERDETTO, decide il MARGINE. Su un
contratto che afferma i suoi numeri una volta sola i ricalchi restano bloccati, ma il
giudice e' molto meno sicuro, e la difesa poggia sul layer lessicale — quello che
oggi ho misurato cieco in tre modi diversi.

✅ DEBITO PAGATO LO STESSO GIORNO — terza cella, confondente ELIMINATO::

    A: CON ripetizione       161 parole  «72»x2   ricalco24 g=0.2   CONTROLLO61 g= 2.8
    B: SENZA (piu' corta)    139 parole  «72»x1   ricalco24 g=0.2   CONTROLLO61 g=64.9
    C: NEUTRO (stessa len)   163 parole  «72»x1   ricalco24 g=0.2   CONTROLLO61 g=73.3

La cella C ha la lunghezza di A (163 contro 161) e una frase di pari registro
giuridico SENZA numeri al posto della ripetizione. **Si comporta come B — anzi
peggio: 73.3 contro 64.9.**
⇒ **E' LA RIPETIZIONE, NON LA LUNGHEZZA.** Il confondente che avevo dichiarato non
c'era: aggiungere contesto neutro non recupera nulla, lo **peggiora** — coerente con
il contorno neutro misurato in `ws5-ricombinare-i-token-della-fonte-da-100.py`
(1.1 -> 100.0 con cinque frasi estranee).
⇒ Quello che tiene basso il punteggio del falso e' **la ripetizione del valore VERO**,
non la quantita' di testo attorno.

⚖️ PUNTO DEBOLE: due fonti, quattro claim, **un solo articolo**. E la differenza fra
le due versioni non e' solo la ripetizione: togliendo quella frase spariscono anche
22 parole di contesto. **Non ho isolato la ripetizione dalla lunghezza** — servirebbe
una terza cella con 22 parole neutre al posto della frase tolta. Non l'ho fatta.

REGIME: build `f5dedf34` · python 3.13.12 · store temporaneo · `run_validation_gate` ·
fonte GDPR art.33 (gdpr-info.eu, 27/08), abbreviata negli elenchi per l'A/B.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-Q2-la-ripetizione-non-e-la-variabile.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, re, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

BASE = ("In the case of a personal data breach, the controller shall without undue delay and, "
 "where feasible, not later than 72 hours after having become aware of it, notify the personal "
 "data breach to the supervisory authority competent in accordance with Article 55, unless the "
 "personal data breach is unlikely to result in a risk to the rights and freedoms of natural "
 "persons. ")
RIPETIZIONE = ("Where the notification to the supervisory authority is not made within 72 hours, it "
 "shall be accompanied by reasons for the delay. ")
CODA = ("The processor shall notify the controller without undue delay after becoming aware of a "
 "personal data breach. The notification referred to in paragraph 1 shall at least describe the "
 "nature of the personal data breach, communicate the name and contact details of the data "
 "protection officer, describe the likely consequences, and describe the measures taken by the "
 "controller. The controller shall document any personal data breaches, comprising the facts, "
 "its effects and the remedial action taken.")

FONTI = [("CON ripetizione (x2)", BASE + RIPETIZIONE + CODA),
         ("SENZA ripetizione (x1)", BASE + CODA)]
CLAIM = [
 ("VERO 72",       "The controller shall notify the personal data breach to the supervisory authority not later than 72 hours after having become aware of it."),
 ("ricalco 24",    "The controller shall notify the personal data breach to the supervisory authority not later than 24 hours after having become aware of it."),
 ("ricalco 48",    "The controller shall notify the personal data breach to the supervisory authority not later than 48 hours after having become aware of it."),
 ("CONTROLLO 61",  "The controller shall notify the personal data breach to the supervisory authority not later than 61 hours after having become aware of it."),
]
print("")
for eti_f, src in FONTI:
    occ72 = len(re.findall(r"(?<![\d.])72(?![\d])", src))
    print("   %-24s (%d parole, «72» x%d)" % (eti_f, len(src.split()), occ72))
    for eti_c, claim in CLAIM:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=src, grounding_llm=None, ground_write=True)
        g = getattr(r, "grounding_score", None)
        ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
              for w in (getattr(r, "warnings", None) or [])]
        print("      %-14s %-10s g=%6s  %s" % (eti_c, getattr(r, "action", "?"),
              ("%.1f" % g) if isinstance(g, (int, float)) else "-", ",".join(ws)[:30] or "-"))
