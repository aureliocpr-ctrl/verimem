# -*- coding: utf-8 -*-
"""M6 — lo STESSO span, tagliato o no: il taglio fa accusare fatti veri?

    python docs/stato-reale/banchi/ws6-m6-il-taglio-appaiato.py

Il banco precedente (`ws6-m6-la-prova-troncata-regge-il-rigiudizio.py`) ha
FALSIFICATO la mia prima predizione: il punteggio di grounding NON cade quando si
rigiudica sulla prova troncata (mediana 0.02 contro 0.00 del controllo). Ma
guardando lo STATUS invece del punteggio, `L4.1` si attivava **3 volte su 10** fra
i troncati e **1 su 10** fra gli interi.

⚠️ TRE CONTRO UNO SU DIECI NON DECIDE NULLA, e c'è un confondente evidente: i
fatti con span lungo hanno fonti più ricche di numeri, quindi danno a `L4.1` più
occasioni di attivarsi **indipendentemente dal troncamento**. I due gruppi non
sono lo stesso materiale.

QUI I DUE GRUPPI SONO LO STESSO MATERIALE: si prendono span **non troncati**
(300-399 caratteri, cioè quello che il giudice ha selezionato per intero) e si
rigiudica ogni fatto DUE VOLTE — una con lo span intero, una con lo span tagliato
a 200. **Una sola variabile: il taglio.**

╔═ PREDIZIONE, scritta PRIMA (fatto 3be3e49bc45f, 12:54) ══════════════════════╗
║  span INTERO     L4.1 si attiva al più 1 volta su 12                         ║
║  span TAGLIATO   L4.1 si attiva almeno 4 volte su 12                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Se il taglio non sposta nulla, il tetto dei 400 è innocuo anche per la riverifica
e M6 si chiude come debito storico puro.

⛔ Store di Aurelio in SOLA LETTURA. Il rigiudizio scrive in un tempdir.
"""
import os
import sqlite3
import tempfile

_tmp = tempfile.mkdtemp(prefix="ws6_m6_taglio_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402

CASA = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
N, TAGLIO = 12, 200

ro = sqlite3.connect("file:%s?mode=ro" % CASA.replace(os.sep, "/"), uri=True)
righe = ro.execute(
    "SELECT id, proposition, grounding_span, grounding_score FROM facts "
    "WHERE grounding_span IS NOT NULL AND length(grounding_span) BETWEEN 300 AND 399 "
    "  AND grounding_score >= 95 ORDER BY created_at DESC LIMIT ?", (N,)).fetchall()
ro.close()

m = Memory()
print("LO STESSO SPAN, TAGLIATO O NO — una sola variabile\n")
print("  %-14s %6s | %-26s | %-26s" % ("fatto", "car.", "span INTERO", "span TAGLIATO a %d" % TAGLIO))
conta = {"intero": 0, "tagliato": 0}
quar = {"intero": 0, "tagliato": 0}

for fid, prop, span, score in righe:
    riga = []
    for nome, testo in (("intero", span), ("tagliato", span[:TAGLIO])):
        r = m.add(prop, topic="ws6/taglio-%s-%s" % (nome, fid), source=testo)
        st = (r.get("status") or "?") if isinstance(r, dict) else "?"
        strati = sorted({str(w.get("layer", "?")) for w in (r.get("warnings") or [])})
        if any(s.startswith("L4.1") for s in strati):
            conta[nome] += 1
        if st == "quarantined":
            quar[nome] += 1
        riga.append("%s [%s]" % ("QUAR" if st == "quarantined" else "amm.",
                                 ",".join(strati) or "-"))
    print("  %-14s %6d | %-26s | %-26s" % (fid, len(span), riga[0][:26], riga[1][:26]))

print("\n" + "=" * 78)
print("  L4.1 si attiva:   span INTERO %d/%d   ·   span TAGLIATO %d/%d"
      % (conta["intero"], len(righe), conta["tagliato"], len(righe)))
print("  quarantinati:     span INTERO %d/%d   ·   span TAGLIATO %d/%d"
      % (quar["intero"], len(righe), quar["tagliato"], len(righe)))
print("\n  la PREDIZIONE era: intero <= 1 su 12 · tagliato >= 4 su 12")
