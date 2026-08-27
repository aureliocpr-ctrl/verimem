# -*- coding: utf-8 -*-
r"""Su un documento legale VERO `L4.1` e' cieco come misurato — MA NON E' SOLO.

    3 giorni      «3» nel testo x8    assenti=0  downgrade  L4.2,L4-grounding
    7 giorni      «7» nel testo x4    assenti=0  downgrade  L4.2,L4-review
    2 copie       «2» nel testo x6    assenti=0  downgrade  L4.2,L4-grounding
    10 anni       «10» nel testo x4   assenti=0  downgrade  L4.2,L4-grounding
    CONTROLLO 61     «61» x0          assenti=1  downgrade  **L4.1**,L4-review
    CONTROLLO 4291   «4291» x0        assenti=1  downgrade  **L4.1**,L4-review

Fonte: `LICENSE` del repo — documento legale VERO, 5535 parole, 25 numeri distinti,
63 occorrenze, densita' 1,1% (il profilo di un contratto). I numeri piu' frequenti
sono cifre singole — 3 x8, 1 x6, 2 x6, 4 x4, 7 x4 — cioe' NUMERI DI CLAUSOLA.

⇒ ① IL MECCANISMO E' CONFERMATO SU FONTE REALE: `assenti=0` per ogni valore che
compare come numero di clausola, `assenti=1` per i due controlli. **`L4.1` parla
SOLO sui controlli.** Non serviva costruire le fonti: un testo legale vero ha per
sua natura le cifre singole che coprono le invenzioni.
⇒ ② MA TUTTI E SEI SONO BLOCCATI, e questo RIDIMENSIONA l'allarme che avevo dato.
I primi quattro cadono per **`L4-grounding`**, non per `L4.1`. Il claim «notice
within 3 days» non e' sostenuto dal testo, e il giudice semantico lo prende.
⇒ ③ ALLORA PERCHE' IN `ws5-Q2-il-gate-annega-sulle-fonti-lunghe.py` IL FALSO PASSAVA?
Perche' li' il claim **ricalcava una riga della fonte** («Gate admission:
noise-rejection 24/24 = 100%, clean-admission 22/24 = 92%») e prendeva grounding
**100.0**: alta sovrapposizione lessicale. Qui il claim inventa una clausola che il
documento non contiene, la sovrapposizione e' bassa, e il grounding lo boccia.

🔑 LA CONGIUNZIONE E' LA COSA PERICOLOSA, non `L4.1` da solo::

    L4.1 cieco  +  ALTA sovrapposizione col testo   ->  PASSA   (caso Q2, g=100)
    L4.1 cieco  +  bassa sovrapposizione            ->  bloccato dal grounding

⇒ Il profilo di rischio non e' «un numero inventato in un documento lungo». E'
**«un claim che RICALCA il documento e cambia un numero comune»** — cioe' esattamente
quello che produce un riassunto automatico: copia la struttura della fonte e sbaglia
una cifra. Le due condizioni si trovano insieme proprio nel caso d'uso reale.

⚖️ E QUESTO CORREGGE IN MEGLIO IL MIO REFERTO: avevo scritto «su un contratto di
quaranta pagine quasi ogni numero a due cifre trova un gemello» lasciando intendere
che bastasse quello. **Non basta.** Serve anche che il claim assomigli alla fonte.
Il difetto resta reale e la sua porta e' piu' stretta di come l'avevo descritta.

📌 PUNTO DEBOLE: sei claim su UNA licenza, e la `LICENSE` non contiene clausole con
giorni o percentuali (per questo i claim inventano cose che il testo non tratta —
ed e' anche il motivo per cui il grounding li prende). ⇒ Su un contratto VERO, che
quelle clausole le contiene, la sovrapposizione sarebbe piu' alta e il rischio
maggiore: **questo banco e' un limite INFERIORE, non una rassicurazione.**

REGIME: build `f5dedf34` · python 3.13.12 · store temporaneo · `valori_non_nella_fonte`
+ `run_validation_gate`, la porta che usa la CLI (`cli.py:1867`).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-documento-legale-vero-L41-cieco-ma-non-solo.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import io, os, re, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.valore_non_nella_fonte import valori_non_nella_fonte
from verimem.anti_confab_gate import run_validation_gate

SRC = io.open("LICENSE", encoding="utf-8", errors="replace").read()

#: claim che un utente scriverebbe riassumendo una licenza, con un valore INVENTATO
CASI = [
 ("3 giorni",   "The licensee must give notice within 3 days of the breach."),
 ("7 giorni",   "The licensee must give notice within 7 days of the breach."),
 ("2 copie",    "The licensee may distribute at most 2 copies of the source."),
 ("10 anni",    "The licence remains valid for 10 years after distribution."),
 ("CONTROLLO 61",   "The licensee must give notice within 61 days of the breach."),
 ("CONTROLLO 4291", "The licensee may distribute at most 4291 copies of the source."),
]
print("")
for eti, claim in CASI:
    val = re.findall(r"(?<![\d.])\d+(?![\d])", claim)[0]
    occ = len(re.findall(r"(?<![\d.])%s(?![\d])" % val, SRC))
    ass = valori_non_nella_fonte(claim, SRC)
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=SRC, grounding_llm=None, ground_write=True)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    print("   %-16s «%s» nel testo x%-2d  assenti=%d  %-10s layers=%s"
          % (eti, val, occ, len(ass), getattr(r, "action", "?"), ",".join(ws)[:30] or "-"))
