"""Chi trattiene i fatti che il GIUDICE APPROVA, e quanto gridano L4.1/L4.2.

DUE POPOLAZIONI, entrambe misurate:
  [A] quarantinati con grounding >=90  — il moat approva e qualcosa li ferma
  [B] AMMESSI  (model_claim, grounding >=90) — il controllo: quanti di loro
      porterebbero comunque un avviso L4.x? Se il tasso e' simile, l'avviso
      non discrimina e il suo valore informativo e' vicino a zero.

I detector lessicali sono deterministici e non chiamano modelli: rieseguirli
sulla proposizione dice quale si accende. E' lo stesso metodo di
`Memory._spiega_le_quarantene`.
"""
import os
import sqlite3
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from verimem.config import CONFIG  # noqa: E402
import verimem.anti_confab_gate as g  # noqa: E402

print("importa da :", g.__file__)
print("store      :", CONFIG.semantic_db)
print()
_TARA = True

con = sqlite3.connect(str(CONFIG.semantic_db))
con.row_factory = sqlite3.Row


def layer_di(prop, source):
    """I layer che si accendono ricalcolando il gate su questa coppia.

    ⚠️ `ground_write=True` E' OBBLIGATORIO: senza, il giudice non gira e
    L4.1/L4.2 — che confrontano il claim CON la fonte — non possono accendersi
    mai. Controllo positivo del righello, sul caso noto:
        nudo               -> []          grounding None
        ground_write=True  -> ['L4.1']    grounding 99.89
    La prima stesura di questo banco dava 0% su ENTRAMBE le popolazioni, ed era
    il righello, non il prodotto.
    """
    try:
        gt = g.run_validation_gate(proposition=prop or "", verified_by=[],
                                   topic=None, agent=None, source=source,
                                   ground_write=True)
    except Exception:
        return None
    return [str(w.get("layer", "")) for w in (getattr(gt, "warnings", None) or [])]


def _taratura():
    """Il banco si RIFIUTA di misurare se il righello non trova il caso noto."""
    noto = layer_di(
        "Con il tetto attivo il committed e 176,6 MB.",
        "Con il tetto attivo il committed e 176.6 MB e il costo per thread "
        "e 32.2 MB.")
    print("taratura: il caso noto L4.1 ->", noto)
    if not noto or not any(str(x).startswith("L4.1") for x in noto):
        print("RIGHELLO ROTTO: non trova nemmeno il caso noto. Non misuro.")
        raise SystemExit(1)
    print()


def famiglia(lay):
    if lay.startswith("L4.1"):
        return "L4.1"
    if lay.startswith("L4.2"):
        return "L4.2"
    if lay.startswith("L4"):
        return "L4-altro"
    if lay.startswith("L1"):
        return "L1"
    if lay.startswith("L3"):
        return "L3"
    return lay or "?"


POPOLAZIONI = [
    ("[A] QUARANTINATI con grounding >=90",
     """SELECT proposition, grounding_span AS src FROM facts
        WHERE status='quarantined' AND superseded_by IS NULL
          AND grounding_score >= 90 ORDER BY created_at DESC LIMIT 150"""),
    ("[B] AMMESSI  con grounding >=90  (il CONTROLLO)",
     """SELECT proposition, grounding_span AS src FROM facts
        WHERE status='model_claim' AND superseded_by IS NULL
          AND grounding_score >= 90 ORDER BY created_at DESC LIMIT 150"""),
]

_taratura()
riassunto = {}
for etichetta, sql in POPOLAZIONI:
    righe = con.execute(sql).fetchall()
    c = Counter()
    con_l42 = con_l41 = senza = illeggibili = 0
    for r in righe:
        lays = layer_di(r["proposition"], r["src"])
        if lays is None:
            illeggibili += 1
            continue
        fam = {famiglia(x) for x in lays if x}
        for f in fam:
            c[f] += 1
        if "L4.2" in fam:
            con_l42 += 1
        if "L4.1" in fam:
            con_l41 += 1
        if not fam:
            senza += 1
    n = len(righe) - illeggibili
    riassunto[etichetta] = (n, con_l41, con_l42, senza)
    print("%s   n=%d" % (etichetta, n))
    if illeggibili:
        print("    (%d non ricalcolabili, esclusi dal conto)" % illeggibili)
    for k, v in c.most_common(8):
        print("      %-10s %3d  (%.0f%%)" % (k, v, 100.0 * v / max(1, n)))
    print("      %-10s %3d  (%.0f%%)" % ("NESSUNO", senza, 100.0 * senza / max(1, n)))
    print()

print("=" * 66)
print("%-38s %6s %6s" % ("", "L4.1", "L4.2"))
for et, (n, a, b, s) in riassunto.items():
    print("%-38s %5.0f%% %5.0f%%   (n=%d)" % (
        et[:38], 100.0 * a / max(1, n), 100.0 * b / max(1, n), n))
print()
(nA, a1, a2, _sA) = list(riassunto.values())[0]
(nB, b1, b2, _sB) = list(riassunto.values())[1]
def rapporto(qa, na, qb, nb):
    pa, pb = qa / max(1, na), qb / max(1, nb)
    return (pa / pb) if pb else float("inf")
print("SEPARAZIONE (quante volte piu' probabile su un quarantinato che su un ammesso):")
print("   L4.1  %.1fx" % rapporto(a1, nA, b1, nB))
print("   L4.2  %.1fx" % rapporto(a2, nA, b2, nB))
print()
print("FALSI ALLARMI (avvisi su fatti che il gate ha AMMESSO):")
print("   L4.1  %d su %d  (%.0f%%)" % (b1, nB, 100.0 * b1 / max(1, nB)))
print("   L4.2  %d su %d  (%.0f%%)" % (b2, nB, 100.0 * b2 / max(1, nB)))
print()
print("Se il rapporto e' vicino a 1, l'avviso NON separa le popolazioni.")
