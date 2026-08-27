# -*- coding: utf-8 -*-
r"""L'AFFERMAZIONE vince sulla collisione, e allungare la fonte RAFFORZA la difesa.

    CORTA (   70 parole)   VERO EUR 40 «40» x1  persist  100.0
                           EUR 4  «4» x1  downgrade 0.5
                           EUR 7  «7» x0  downgrade 0.4
                           EUR 3  «3» x1  downgrade 0.5
                           CONTROLLO 4291 x0  downgrade 0.2
    LUNGA ( 5605 parole)   VERO EUR 40 «40» x1  persist  100.0
                           EUR 4  «4» x5  downgrade 0.2
                           EUR 7  «7» x4  downgrade 0.2
                           EUR 3  «3» x9  downgrade 3.5
                           CONTROLLO 4291 x0  downgrade 0.4

Paga il debito del decimo banco: «126 parole, fonte corta ⇒ **la collisione non ha
spazio per giocare**; e il caso EUR 4 e' uno solo». Qui la stessa clausola (dir. UE
2011/7 art.6, verbatim) e' immersa nella `LICENSE` del repo — 5535 parole densissime
di cifre singole — cosi' che i valori inventati abbiano **molti** gemelli.

⇒ ① L'AFFERMAZIONE VINCE ANCHE CON SPAZIO. Il «3» collide **nove volte** e resta
bloccato; il «4» cinque volte, il «7» quattro. Tre casi invece di uno.
⇒ ② E I PUNTEGGI **SCENDONO** ALLUNGANDO LA FONTE (0.5 → 0.2), non salgono. ⇒ **Su un
valore AFFERMATO, piu' testo attorno significa piu' difesa**, perche' il claim risulta
sempre piu' isolato rispetto a cio' che il documento dice davvero.
⇒ ③ E' L'OPPOSTO di cio' che accade sui valori NON affermati, dove allungare la fonte
apre la strada (`ws5-Q2-il-gate-annega-sulle-fonti-lunghe.py`: il falso passa a 10000
parole) e il contorno neutro porta 1.1 → 100.0.

🔑 LA REGOLA FINALE, ora con i controlli in ENTRAMBE le direzioni::

    valore AFFERMATO dal testo   -> difeso; collisione, lunghezza e ripetizione
                                    NON lo scalfiscono (anzi la lunghezza AIUTA)
    valore NON affermato         -> esposto; e li' collisione, lunghezza, forma
      (riferimento, omissione,      del numero e ricalco decidono tutto
       numero a parole, altra unita')

⇒ **Il gate difende cio' che il testo AFFERMA. Tutto il resto della mia serie di
banchi descrive cosa succede FUORI da quel perimetro.** In un contratto: penali,
termini e importi sono dentro; rimandi, allegati e sfumature sono fuori.

✅ DEBITO CHIUSO SENZA UN NUOVO BANCO — il dato su testo OMOGENEO c'era gia'.
Il punto debole qui sotto («due testi eterogenei incollati») e' gia' coperto da
`ws5-Q2-chiusura-la-congiunzione-su-testo-legale.py`, dove la fonte e' la `LICENSE`
INTERA — 5535 parole, un solo testo legale omogeneo::

    «version 3»  VERO verbatim              persist   100.0   <- controllo +
    «version 2»  ricalco su AFFERMATO       downgrade   0.2   <- difeso
    «section 7»  ricalco su RIFERIMENTO     persist    99.1   <- esposto, zero layer

⇒ **Stessi numeri del banco eterogeneo (0.2 sul valore affermato).** L'eterogeneita'
NON era un confondente: la regola «afferma = difeso, riferimento = esposto» vale
identica su un testo omogeneo e lungo.
🔑 Terza volta in una serata che **il dato o lo strumento esisteva gia'** (dopo
`doctor` e `valori_scritti_a_parole`): la regola «prima di costruire un banco chiedi
se ce l'hai gia'» vale anche sui **propri** banchi di due ore prima.

⚖️ PUNTO DEBOLE: la fonte lunga e' `art.6 + LICENSE`, cioe' **due testi eterogenei
incollati** — un contratto vero e' omogeneo, e un giudice semantico potrebbe
comportarsi diversamente su un testo coerente. **Il verso dell'effetto e' misurato,
la sua entita' su un documento omogeneo no.** E il VERO EUR 40 passa a 100.0 in
entrambe: il controllo positivo non distingue le due condizioni, quindi non dice se
la fonte lunga aiuti anche i veri.

REGIME: build `f5dedf34` · python 3.13.12 · store temporaneo · `run_validation_gate`
(la porta della CLI, `cli.py:1867`) · art.6 da legislation.gov.uk, 27/08.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-l-affermazione-vince-sulla-collisione.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import io, os, re, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

ART6 = ("Member States shall ensure that, where interest for late payment becomes payable in "
 "commercial transactions in accordance with Article 3 or 4, the creditor is entitled to obtain "
 "from the debtor, as a minimum, a fixed sum of EUR 40. Member States shall ensure that the fixed "
 "sum referred to in paragraph 1 is payable without the necessity of a reminder and as "
 "compensation for the creditor's own recovery costs. ")
LUNGO = io.open("LICENSE", encoding="utf-8", errors="replace").read()

FONTI = [("CORTA (solo art.6)", ART6),
         ("LUNGA (art.6 + LICENSE)", ART6 + LUNGO)]
CASI = [
 ("VERO EUR 40",       "The creditor is entitled to obtain from the debtor, as a minimum, a fixed sum of EUR 40."),
 ("AFFERMATO: EUR 4",  "The creditor is entitled to obtain from the debtor, as a minimum, a fixed sum of EUR 4."),
 ("AFFERMATO: EUR 7",  "The creditor is entitled to obtain from the debtor, as a minimum, a fixed sum of EUR 7."),
 ("AFFERMATO: EUR 3",  "The creditor is entitled to obtain from the debtor, as a minimum, a fixed sum of EUR 3."),
 ("CONTROLLO 4291",    "The creditor is entitled to obtain from the debtor, as a minimum, a fixed sum of EUR 4291."),
]
print("")
for eti_f, src in FONTI:
    print("   %-26s (%5d parole)" % (eti_f, len(src.split())))
    for eti_c, claim in CASI:
        v = re.findall(r"(?<![\d.])\d+(?![\d])", claim)[0]
        occ = len(re.findall(r"(?<![\d.])%s(?![\d])" % v, src))
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=src, grounding_llm=None, ground_write=True)
        g = getattr(r, "grounding_score", None)
        print("      %-19s «%s» x%-2d  %-10s g=%6s" % (eti_c, v, occ,
              getattr(r, "action", "?"), ("%.1f" % g) if isinstance(g, (int, float)) else "-"))
