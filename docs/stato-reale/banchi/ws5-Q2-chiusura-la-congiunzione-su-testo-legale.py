# -*- coding: utf-8 -*-
r"""CHIUSURA Q2 — su un testo legale VERO il ricalco con numero di clausola passa 2/3.

    VERO verbatim       «3»    x8   persist    g= 100.0  -                    <- controllo +
    ricalco + 2 (x6)    «2»    x6   downgrade  g=   0.2  L4.2,L4-grounding
    ricalco + 7 (x4)    «7»    x4   persist    g=  99.1  NESSUN LAYER         <- passa
    VERO verbatim 2     «10»   x4   persist    g= 100.0  -                    <- controllo +
    ricalco + 3 (x8)    «3»    x8   persist    g= 100.0  L4.2                 <- passa
    CONTROLLO 61        «61»   x0   downgrade  g=  35.5  **L4.1**,L4-negazione
    CONTROLLO 4291      «4291» x0   downgrade  g=  91.9  **L4.1**

Fonte: `LICENSE` del repo (AGPL-3.0), documento legale VERO, 5535 parole. I claim
sono RICALCHI QUASI VERBATIM di frasi VERE del testo, con UN SOLO numero cambiato,
scelto fra quelli COMUNI nel documento (numeri di clausola).

    frase vera:  «Sublicensing is not allowed; section 10 makes it unnecessary.»
    ricalco:     «Sublicensing is not allowed; section  7 makes it unnecessary.»
    esito:       persist, g=99.1, **nessun layer**

⇒ DUE FALSI SU TRE ENTRANO, uno a 99.1 con ZERO layer e uno a 100.0 con il solo
`L4.2` (che avvisa, non veta). ⇒ **La congiunzione «ricalco del testo + numero
comune» e' il profilo che passa, e su un documento legale si presenta da sola**:
un riassunto automatico ricalca la struttura della fonte per costruzione, e i numeri
di clausola sono cifre singole per convenzione tipografica.

✅ I CONTROLLI TENGONO IN ENTRAMBE LE DIREZIONI, ed e' cio' che rende leggibile il
risultato: i due VERI verbatim passano (100.0), i due numeri ASSENTI dal documento
(61, 4291) sono bloccati e `L4.1` **parla solo li'**. Il banco separa.

⚖️ E UN CASO SU TRE E' BLOCCATO — `version 2` al posto di `version 3`, g=0.2. Non
lo nascondo e non so spiegarlo con certezza: la frase parla dell'identita' della
licenza stessa, che il documento afferma molte volte, e il giudice semantico
probabilmente la vede contraddetta piu' che non-sostenuta. ⇒ **Il difetto e'
statistico, non deterministico: dipende da quanto quella particolare affermazione
e' ridondante nel testo.**

⇒ COSA CHIUDE, rispetto ai tre banchi precedenti:
 · `ws5-Q2-il-gate-annega-sulle-fonti-lunghe.py` diceva «e' la lunghezza» — CORRETTO poi
 · `ws5-Q2bis-la-rarita-del-numero-decide.py` diceva «e' la rarita' del numero» — vero ma
   non sufficiente
 · `ws5-documento-legale-vero-L41-cieco-ma-non-solo.py` mostrava che il grounding
   copre `L4.1` quando la sovrapposizione e' bassa
 · **questo** mostra che quando la sovrapposizione e' ALTA — cioe' nel caso d'uso reale
   — la copertura sparisce e il falso entra.

📌 PUNTO DEBOLE: sette claim su UNA licenza, e una licenza non e' un contratto — non
ha clausole in giorni ne' percentuali. **Il profilo di rischio e' dimostrato, la sua
FREQUENZA su contratti veri no.** Serve un corpus legale con clausole quantitative:
chi lo ha chiude la domanda in mezz'ora.

REGIME: build `f5dedf34` · python 3.13.12 · store temporaneo · `run_validation_gate`,
la porta che usa la CLI (`cli.py:1867`) · fonte intera, 5535 parole.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-Q2-chiusura-la-congiunzione-su-testo-legale.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import io, os, re, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate
SRC = io.open("LICENSE", encoding="utf-8", errors="replace").read()

CASI = [
 ("VERO verbatim",  '"This License" refers to version 3 of the GNU Affero General Public License.'),
 ("ricalco + 2 (x6)", '"This License" refers to version 2 of the GNU Affero General Public License.'),
 ("ricalco + 7 (x4)", "Sublicensing is not allowed; section 7 makes it unnecessary."),
 ("VERO verbatim 2", "Sublicensing is not allowed; section 10 makes it unnecessary."),
 ("ricalco + 3 (x8)", 'This requirement modifies the requirement in section 3 to "keep intact all notices".'),
 ("CONTROLLO 61",    "Sublicensing is not allowed; section 61 makes it unnecessary."),
 ("CONTROLLO 4291",  '"This License" refers to version 4291 of the GNU Affero General Public License.'),
]
print("")
for eti, claim in CASI:
    v = re.findall(r"(?<![\d.])\d+(?![\d])", claim)[0]
    occ = len(re.findall(r"(?<![\d.])%s(?![\d])" % v, SRC))
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=SRC, grounding_llm=None, ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    print("   %-19s «%s» x%-2d  %-10s g=%6s  %s"
          % (eti, v, occ, getattr(r, "action", "?"),
             ("%.1f" % g) if isinstance(g, (int, float)) else "-", ",".join(ws)[:30] or "-"))
