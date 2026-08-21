"""Il giudice del moat davanti a una SOURCE TABELLARE.

A/B a variabile singola: lo STESSO claim, due source che contengono gli STESSI
numeri — una e' l'output grezzo di uno strumento (tabella/log), l'altra e' la
stessa informazione in prosa. Se il punteggio crolla sulla tabella, il gate
quarantina fatti veri ogni volta che qualcuno salva l'output di un comando —
cioe' il caso d'uso principale di questo prodotto.

Fuori da pytest: sotto pytest l'embedder e' uno stub su SHA-256.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from verimem import Memory  # noqa: E402
import verimem.client as _c  # noqa: E402

print("importa verimem da : %s" % _c.__file__)
print()

CASI = [
    # (etichetta, claim, source TABELLARE, source in PROSA)
    ("exit code",
     "Sull albero senza la cura il doctor sul regime rotto stampa EXIT 1 e "
     "sull albero con la cura stampa EXIT 2.",
     "SENZA CURA  pulito  EXIT=0\n"
     "SENZA CURA  rotto   EXIT=1\n"
     "--- con la cura ---\n"
     "rotto  EXIT=2",
     "Sull albero senza la cura il regime rotto stampa EXIT 1. "
     "Sull albero con la cura lo stesso regime stampa EXIT 2."),
    ("conteggio test",
     "Il file di test da' 24 passed sull albero con la cura e 13 failed con "
     "11 passed sull albero senza.",
     "tests/test_x.py ........................    [100%]\n"
     "24 passed in 5.23s\n"
     "--- albero senza la cura ---\n"
     "13 failed, 11 passed in 6.37s",
     "Il file di test da' 24 passed sull albero con la cura. "
     "Sull albero senza la cura da' 13 failed e 11 passed."),
    ("finestra",
     "Nelle ultime 24 ore i quarantinati sono 25 e negli ultimi 7 giorni "
     "sono 136.",
     "finestra          quar.    vuoto     gate\n"
     "ultime 24h           25       0%       56%\n"
     "ultimi 7g           136       0%       16%",
     "Nelle ultime 24 ore i quarantinati sono 25. "
     "Negli ultimi 7 giorni i quarantinati sono 136."),
    ("coppie",
     "Le coppie che non avverrebbero piu' sono 27 e quelle che inizierebbero "
     "ad avvenire sono 1.",
     "  NON avverrebbero piu' :   27  (1.4%)   entrambi >=90: 26\n"
     "  INIZIEREBBERO         :    1  (0.1%)   entrambi >=90: 0",
     "Le coppie che non avverrebbero piu' sono 27. "
     "Le coppie che inizierebbero ad avvenire sono 1."),
]


def giudica(claim, source):
    d = tempfile.mkdtemp()
    m = Memory(path=os.path.join(d, "s.db"))
    r = m.add(claim, topic="t", source=source)
    return (r.get("grounding_score"), r.get("status"),
            r.get("quarantined_by"), r.get("moat"))


print("%-16s %-22s %-22s" % ("caso", "source TABELLARE", "source in PROSA"))
print("-" * 74)
crolli = 0
for et, claim, tab, prosa in CASI:
    gt, st, byt, mt = giudica(claim, tab)
    gp, sp, byp, mp = giudica(claim, prosa)
    delta = (gp or 0) - (gt or 0)
    if (gt or 0) < 40 <= (gp or 0):
        crolli += 1
        segno = "  <- SOLO la tabella cade"
    else:
        segno = ""
    print("%-16s %6.2f %-15s %6.2f %-15s  delta %+7.2f%s" % (
        et, gt or -1, st, gp or -1, sp, delta, segno))
print("-" * 74)
print("casi in cui la TABELLA cade e la PROSA passa: %d su %d" % (crolli, len(CASI)))
print()
print("La soglia di ammissione in vigore e' 40/100.")
