# -*- coding: utf-8 -*-
"""Una citazione VERA viene rifiutata, e serve una GIUNTURA per farla cadere.

Trovato mentre misuravo altro: nel controllo positivo di
`ws3-quale-famiglia-chiude-la-classe.py`, 4 citazioni vere su 16 sono
rifiutate. Due (`errore` IT+EN) restano rifiutate anche a famiglia lessicale
SPENTA, quindi le ferma L4 — e nessuna spiegazione linguistica regge: e' un CE
inglese (vocab_size 128100) su testo inglese.

    fonte  «ConnectionError: could not reach db-primary:5432 after 3 attempts
            (timeout 5s). Fallback to db-replica succeeded.»
    claim  «The db-primary database was unreachable on port 5432.»
    esito  quarantined, grounding 0.9

La parafrasi e' ineccepibile. Il CE, che in casa misura 97-99 sugli entailment
(grounding_gate.py:522-531), da' 0.9.

═══ MISURATO — e la mia ipotesi di partenza cade a meta' ═══
Ipotizzavo «il CE crolla sui log perche' non sono prosa». Falso in quella forma:

    variante                     esito         g     layer
    A traceback + numero         quarantined   0.9   L4-grounding+L4.2   (EN)
    A traceback + numero         quarantined   1.4   +L4-negazione       (IT)
    B PROSA     + numero         admitted        -   L4.2
    C traceback SENZA numero     admitted        -   -
    D PROSA + numero FALSO       quarantined   0.4   L4-grounding+L4.1   <- controllo

C dimostra che sul traceback, senza numero, il CE riconosce benissimo
l'entailment. ⇒ Non e' la forma da sola, e non e' il numero da solo: e' la
GIUNTURA fra una fonte che porta il numero AGGLUTINATO (`db-primary:5432`) e
un claim che lo cita isolato (`port 5432`). Togline uno qualunque e passa.

⚖️ IL CONTROLLO D E' CIO' CHE RENDE LEGGIBILE IL RESTO: sulla prosa un claim
con la porta SBAGLIATA (6543) resta quarantinato a g=0.4. La prosa non «fa
passare tutto» — senza questa riga, B sarebbe indistinguibile da un falso verde.

📌 Chi accusa: in B il layer L4.2 si accende COMUNQUE (avviso, non veto). Il
veto in A viene dal grounding a 0.9, non da L4.2.

🔗 GEMELLO, stessa serata: un save di lead-audit quarantinato perche' L4.1
leggeva la data «25/08» come due valori assenti dalla fonte. Stessa famiglia —
l'estrazione dei numeri da testo che non e' prosa. La voce «le date non sono
quantita'» va quindi allargata: i numeri AGGLUTINATI non sono assenti.

Regime: porta pubblica `verimem remember --source`, store temporaneo vuoto,
FUORI pytest. SHA 397c6375, 25/08.
"""
import contextlib, io, os, re, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_prosa_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"
from verimem.cli import main

TRACE_EN = ("ConnectionError: could not reach db-primary:5432 after 3 attempts "
            "(timeout 5s). Fallback to db-replica succeeded.")
TRACE_IT = ("ConnectionError: impossibile raggiungere db-primary:5432 dopo 3 tentativi "
            "(timeout 5s). Fallback su db-replica riuscito.")
PROSA_EN = ("The database db-primary could not be reached on port 5432 after three "
            "attempts, each with a timeout of 5 seconds. The fallback to the replica "
            "db-replica then succeeded.")
PROSA_IT = ("Il database db-primary non e' stato raggiunto sulla porta 5432 dopo tre "
            "tentativi, ciascuno con un timeout di 5 secondi. Il ripiego sulla replica "
            "db-replica e' poi riuscito.")
CLAIM_EN = "The db-primary database was unreachable on port 5432."
CLAIM_IT = "Il database db-primary non era raggiungibile sulla porta 5432."
SENZA_EN = "The db-primary database was unreachable."
SENZA_IT = "Il database db-primary non era raggiungibile."
FALSO_EN = "The db-primary database was unreachable on port 6543."
FALSO_IT = "Il database db-primary non era raggiungibile sulla porta 6543."

CASI = [
 ("A traceback   +claim", "EN", CLAIM_EN, TRACE_EN, True),
 ("A traceback   +claim", "IT", CLAIM_IT, TRACE_IT, True),
 ("B PROSA       +claim", "EN", CLAIM_EN, PROSA_EN, True),
 ("B PROSA       +claim", "IT", CLAIM_IT, PROSA_IT, True),
 ("C traceback   -numero", "EN", SENZA_EN, TRACE_EN, True),
 ("C traceback   -numero", "IT", SENZA_IT, TRACE_IT, True),
 ("D PROSA  CONTROLLO falso", "EN", FALSO_EN, PROSA_EN, False),
 ("D PROSA  CONTROLLO falso", "IT", FALSO_IT, PROSA_IT, False),
]
_L = re.compile(r"\b(L1(?:\.\d+)?|L3[\w-]*|L4(?:\.\d+)?[\w-]*|store-screen)\b")

print("%-26s %-3s %-6s %-12s %6s  %s" % ("variante","lg","vero","esito","g","layer"))
for nome, lg, claim, src, vero in CASI:
    buf = io.StringIO(); sys.argv = ["verimem","remember",claim,"--source",src]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf): main()
    except SystemExit: pass
    o = buf.getvalue()
    e = ("admitted" if re.search(r"\badmitted\b",o) else
         "quarantined" if re.search(r"\bquarantined\b",o) else "?")
    m = re.search(r"grounding ([\d.]+)", o)
    print("%-26s %-3s %-6s %-12s %6s  %s"
          % (nome, lg, "SI" if vero else "no", e,
             ("%.1f"%float(m.group(1))) if m else "-",
             "+".join(sorted(set(_L.findall(o)))) or "-"))
