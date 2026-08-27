# -*- coding: utf-8 -*-
r"""NON e' la lunghezza: e' la RARITA' del numero. Le cifre singole cadono a 200 parole.

    valore inventato   collide a        occorrenze nella fonte
    3                  200 parole       2
    9                  200 parole       2
    7                  500 parole       1
    47                 MAI (>7000)      0
    83                 MAI (>7000)      0
    617                MAI (>7000)      0
    4291               MAI (>7000)      0

A/B a fonte fissa (`README.md`, documento VERO, 7107 parole): cambia SOLO il valore
inventato nel claim, tutto il resto e' identico.

⇒ CORREGGE IL REFERTO Q2 (`ws5-Q2-il-gate-annega-sulle-fonti-lunghe.py`), che diceva
«il gate annega sulle fonti lunghe» con la soglia a 4000-4500 parole. **Sbagliato:**
quella era la soglia del valore 92 su QUEL documento. La variabile vera e' un'altra:
**`L4.1` smette di vedere un valore inventato appena quel valore COMPARE ALTROVE
nella fonte, e i numeri comuni compaiono subito.**
⇒ La lunghezza non e' la causa: e' il **moltiplicatore** della probabilita' di
collisione. La causa e' che il confronto avviene su **valori nudi, senza contesto**.

🚨 PERCHE' E' PEGGIO DI COME L'AVEVO SCRITTO. Il referto Q2 rassicurava
implicitamente chi lavora su documenti corti: «serve un contratto di quaranta
pagine». **Falso: bastano 200 parole**, meno di una pagina, se il numero inventato
e' una cifra singola. E le cifre singole sono **esattamente quelle dei contratti** —
«3 rate», «7 giorni», «9 mesi», «2 testimoni». ⇒ Il gate protegge i numeri RARI
(47, 617, 4291: mai caduti in 7000 parole) e non protegge quelli COMUNI, che sono
quelli che contano.

⚖️ E CORREGGE ANCHE LA MIA PREDIZIONE, che avevo dichiarato prima: «su un documento
POVERO di numeri il falso reggera' piu' a lungo». `README.md` ha densita' 7,7%
contro il 19,2% di `BENCHMARKS.md` — **2,5 volte piu' povero** — e il crollo arriva
**molto prima** (1000 parole invece di 4500). La densita' del documento non e' la
variabile: lo e' la frequenza del SINGOLO valore inventato.

📌 IL PUNTO DEBOLE DI QUESTO BANCO: la soglia «200 parole» dipende comunque dal
documento — su un testo senza cifre singole nemmeno il 3 collide. Il claim e' uno
solo, variato in sette valori: **sette celle, nessuna n=1, ma una sola struttura di
frase**. E non ho provato i decimali (`3.5`) ne' i valori con unita' (`7 giorni` vs
`7%`), dove il confronto potrebbe comportarsi diversamente.

REGIME: build `f5dedf34` · python 3.13.12 · fonte `README.md` (7107 parole, densita'
7,7%) · store temporaneo · nessuna delle 10 variabili d'ambiente e' letta da
`anti_confab_gate.py`; qui si chiama direttamente `valori_non_nella_fonte`, che e' la
funzione su cui `L4.1` decide (`anti_confab_gate.py:2455`).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-Q2bis-la-rarita-del-numero-decide.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import io, os, re, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

DOC = io.open("README.md", encoding="utf-8", errors="replace").read()
i = DOC.index("0/10 IT, 0/10 EN")
tok = DOC.split(); centro = len(DOC[:i].split())

def soglia(valore):
    """A quante parole di fonte il valore smette di risultare ASSENTE."""
    claim = "The outright contradiction with a negation is admitted %s/10 IT and 0/10 EN." % valore
    for parole in (200, 500, 1000, 2000, 3000, 5000, 7000):
        a = max(0, centro - parole // 2)
        src = " ".join(tok[a:a + parole])
        if not valori_non_nella_fonte(claim, src):
            occ = len(re.findall(r"(?<![\d.])%s(?![\d])" % re.escape(valore), src))
            return parole, occ
    return None, 0

print("")
print("   valore inventato   collide a       occorrenze nella fonte")
for v in ("7", "3", "9", "47", "83", "617", "4291"):
    p, occ = soglia(v)
    print("   %-18s %-15s %d" % (v, ("%d parole" % p) if p else "MAI (>7000)", occ))
