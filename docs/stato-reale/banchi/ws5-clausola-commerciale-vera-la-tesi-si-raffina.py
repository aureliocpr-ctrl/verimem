# -*- coding: utf-8 -*-
r"""Clausola commerciale VERA: la tesi regge 3 su 4, e il quarto caso la RAFFINA.

    fonte: direttiva UE 2011/7 art.6 verbatim (legislation.gov.uk), 126 parole

    VERO EUR 40           «40»   x1   persist    g= 100.0   <- controllo +
    VERO Article 3        «3»    x1   persist    g= 100.0   <- controllo +
    AFFERMATO: EUR 50     «50»   x0   downgrade  g=   0.2   <- come predetto
    AFFERMATO: EUR 4      «4»    x1   downgrade  g=   0.2   <- COLLIDE e cade lo stesso
    RIFERIMENTO: Art 1    «1»    x2   persist    g=  99.9   <- come predetto
    RIFERIMENTO: par 3    «3»    x1   downgrade  g=   0.3   <- CONTRO la predizione
    CONTROLLO 4291      «4291»   x0   downgrade  g=   0.1   <- controllo -

PAGA L'ULTIMO DEBITO del referto Q2: «manca un contratto commerciale vero, con
clausole quantitative affermate UNA VOLTA SOLA». Questa fonte ha entrambe le
categorie sullo STESSO testo: un importo affermato una volta («a fixed sum of
EUR 40») e riferimenti numerici («Article 3 or 4», «paragraph 1» due volte).

⇒ ① LA META' «AFFERMATI» REGGE, e meglio di come l'avevo previsto. `EUR 50`
(assente) e `EUR 4` (**presente**, x1, dentro «Article 3 or 4») sono **entrambi
bloccati a 0.2**. ⇒ **Su un valore AFFERMATO la collisione non salva il falso**: il
claim contraddice un'affermazione esplicita, e il giudice lo prende comunque.
Questo e' il caso commerciale che conta — penali, termini, importi.
⇒ ② LA META' «RIFERIMENTI» REGGE A META'. «Article 1» al posto di «Article 3 or 4»
**entra a 99.9**, come previsto. Ma «paragraph 3» al posto di «paragraph 1» e'
**bloccato**.

🔑 LA DIFFERENZA FRA I DUE RIFERIMENTI, ed e' il raffinamento::

    «Article 3 or 4»   compare 1 volta   -> il ricalco PASSA (99.9)
    «paragraph 1»      compare 2 volte   -> il ricalco CADE (0.3)

⇒ **Non e' «affermati contro riferimenti»: e' QUANTO L'AFFERMAZIONE E' ANCORATA NEL
TESTO.** Un riferimento ripetuto due volte si comporta come un valore affermato; un
valore citato una volta sola e' esposto. ⇒ Coerente con
`ws5-Q2-la-ripetizione-non-e-la-variabile.py`, dove togliendo la seconda occorrenza
di «72 hours» il margine del controllo passava da 2.8 a 73.3: **la ripetizione non
cambia la NATURA del valore, cambia quanto e' difeso.**

⚖️ ⇒ LA REGOLA FINALE, piu' stretta e piu' utile delle due precedenti: **il gate
difende cio' che il testo AFFERMA e RIPETE. Un numero citato una volta sola — sia
esso un importo o un rimando — e' il punto esposto.** In un contratto vero i termini
e le penali sono di solito ripetuti (testo e tabella); i rimandi agli allegati no.

⚠️ PUNTO DEBOLE: sette claim su **126 parole**. La fonte e' corta, quindi la
collisione non ha spazio per giocare — su un contratto di quaranta pagine il «4» che
qui cade potrebbe trovare gemelli piu' plausibili. **E' un limite SUPERIORE alla
protezione.** E il caso `EUR 4` e' l'unico dove affermazione e collisione si scontrano:
uno solo, non basta a chiudere il punto.

REGIME: build `f5dedf34` · python 3.13.12 · store temporaneo · `run_validation_gate`
(la porta che usa la CLI, `cli.py:1867`) · fonte scaricata da legislation.gov.uk il 27/08.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-clausola-commerciale-vera-la-tesi-si-raffina.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, re, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

SRC = ("Member States shall ensure that, where interest for late payment becomes payable in "
 "commercial transactions in accordance with Article 3 or 4, the creditor is entitled to obtain "
 "from the debtor, as a minimum, a fixed sum of EUR 40. Member States shall ensure that the fixed "
 "sum referred to in paragraph 1 is payable without the necessity of a reminder and as "
 "compensation for the creditor's own recovery costs. The creditor shall, in addition to the "
 "fixed sum referred to in paragraph 1, be entitled to obtain reasonable compensation from the "
 "debtor for any recovery costs exceeding that fixed sum and incurred due to the debtor's late "
 "payment. This could include expenses incurred, inter alia, in instructing a lawyer or employing "
 "a debt collection agency.")

CASI = [
 ("VERO EUR 40",        "The creditor is entitled to obtain from the debtor, as a minimum, a fixed sum of EUR 40."),
 ("VERO Article 3",     "Interest for late payment becomes payable in accordance with Article 3 or 4."),
 ("AFFERMATO: EUR 50",  "The creditor is entitled to obtain from the debtor, as a minimum, a fixed sum of EUR 50."),
 ("AFFERMATO: EUR 4",   "The creditor is entitled to obtain from the debtor, as a minimum, a fixed sum of EUR 4."),
 ("RIFERIMENTO: Art 1", "Interest for late payment becomes payable in accordance with Article 1 or 4."),
 ("RIFERIMENTO: par 3", "The fixed sum referred to in paragraph 3 is payable without the necessity of a reminder."),
 ("CONTROLLO 4291",     "The creditor is entitled to obtain from the debtor, as a minimum, a fixed sum of EUR 4291."),
]
print("")
print("   fonte: dir. 2011/7 art.6 verbatim, %d parole" % len(SRC.split()))
for eti, claim in CASI:
    v = re.findall(r"(?<![\d.])\d+(?![\d])", claim)[0]
    occ = len(re.findall(r"(?<![\d.])%s(?![\d])" % v, SRC))
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=SRC, grounding_llm=None, ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    print("   %-21s «%s» x%-2d  %-10s g=%6s  %s"
          % (eti, v, occ, getattr(r, "action", "?"),
             ("%.1f" % g) if isinstance(g, (int, float)) else "-", ",".join(ws)[:26] or "-"))
