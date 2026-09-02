# -*- coding: utf-8 -*-
"""M6, controllo: un `grounding_score` può esistere SENZA che ci fosse una fonte?

Sul corpus **1167 fatti hanno un punteggio di grounding e né la firma né il testo
della fonte** — 575 di essi a `100.0`. Due letture opposte:

  (a) avevano una fonte, e l'hanno PERSA        -> un difetto, e grosso
  (b) il punteggio si assegna anche senza fonte -> nessun difetto, solo un campo
                                                   che non significa quello che credo

Questo banco decide fra le due **chiedendolo al prodotto** invece di dedurlo:
scrive due fatti identici, uno CON e uno SENZA `source`, e legge cosa resta nelle
tre colonne. Se senza fonte il punteggio resta nullo, la lettura (b) cade e i
1167 avevano una fonte.

⛔ Store ISOLATO in tempdir: non tocca lo store di Aurelio.
"""
import os
import sqlite3
import tempfile

_tmp = tempfile.mkdtemp(prefix="ws6_m6_score_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402

FRASE = "Il registro elenca tre bancali usciti dal deposito il nove giugno."
FONTE = "Registro di magazzino: bancali usciti il 9 giugno, numero tre."

m = Memory()
esiti = []
for etichetta, src in (("CON source", FONTE), ("SENZA source", None)):
    r = m.add(FRASE, topic="ws6/m6-score-%s" % etichetta.split()[0].lower(),
              **({"source": src} if src else {}))
    esiti.append((etichetta, r.get("id") if isinstance(r, dict) else None,
                  r.get("status") if isinstance(r, dict) else "?"))

db = os.path.join(_tmp, "semantic", "semantic.db")
con = sqlite3.connect("file:%s?mode=ro" % db.replace(os.sep, "/"), uri=True)
print("UN PUNTEGGIO PUO' ESISTERE SENZA FONTE?\n")
print("  %-14s %-12s %-10s %-10s %s" % ("scrittura", "status", "score", "firma", "span"))
for etichetta, fid, st in esiti:
    r = con.execute("SELECT grounding_score, source_signature, grounding_span "
                    "FROM facts WHERE id=?", (fid,)).fetchone() if fid else None
    if not r:
        print("  %-14s %-12s  (fatto non trovato: %s)" % (etichetta, st, fid))
        continue
    score = "NULL" if r[0] is None else round(float(r[0]), 2)
    firma = "NULL" if not r[1] else "presente"
    span = "NULL" if not r[2] else "%d car." % len(r[2])
    print("  %-14s %-12s %-10s %-10s %s" % (etichetta, st, score, firma, span))
con.close()

print("\n  score NULL senza fonte  -> il punteggio IMPLICA una fonte:")
print("                             i 1167 ne avevano una e non c'e' piu'")
print("  score non nullo senza fonte -> il campo non significa «giudicato»,")
print("                             e i 1167 non sono un difetto")
