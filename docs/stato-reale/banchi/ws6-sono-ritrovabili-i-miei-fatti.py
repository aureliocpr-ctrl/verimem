"""I fatti che ho scritto stanotte sono ritrovabili?  (seconda versione)

La prima ha misurato la popolazione SBAGLIATA: filtravo su writer_role='user',
che non distingue le istanze — tutte e otto scrivono cosi'. Qui parto dagli ID
dei fatti che ho salvato io, letti dai log dei miei `verimem save`.

Righello onesto: la query si costruisce dal TOPIC riscritto in parole, NON dalla
proposizione (sarebbe il caso facile, gia' caduto nel doc 37).
"""
import os
import sqlite3
import sys

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10

# Gli id li estrae la shell dai log e li passa qui in un file: il `/tmp` di Git
# Bash non e' quello che Python vede su Windows, e cercarli da qui torna vuoto.
ELENCO = sys.argv[1] if len(sys.argv) > 1 else ""
miei = set()
if ELENCO and os.path.exists(ELENCO):
    with open(ELENCO, encoding="utf-8") as fh:
        miei = {r.strip() for r in fh if r.strip()}
print("id ammessi letti da %s: %d" % (ELENCO or "(nessun file)", len(miei)))
if not miei:
    raise SystemExit("nessun id: senza la popolazione non si misura nulla")

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()
ph = ",".join("?" * len(miei))
righe = c.execute(
    "SELECT id, topic FROM facts WHERE id IN (%s)" % ph, tuple(miei)).fetchall()
con.close()
print("di questi, presenti nello store: %d" % len(righe))

per_topic = {}
for fid, topic in righe:
    per_topic.setdefault(str(topic), set()).add(fid)
print("topic distinti miei: %d" % len(per_topic))


def query_dal_topic(t):
    return t.split("/", 1)[-1].replace("-", " ").replace("_", " ").strip()


from verimem.client import Memory   # noqa: E402

m = Memory(DB)
trovati = attesi = 0
degradate = 0
print("\n%-2s %-38s %8s  %s" % ("", "query (dal topic)", "trovati", "regime"))
for topic, ids in sorted(per_topic.items()):
    q = query_dal_topic(topic)
    try:
        res = m.recall(q, k=K)
    except Exception as e:                      # noqa: BLE001
        print("!  %-38s  ERRORE %s" % (q[:38], type(e).__name__))
        attesi += len(ids)
        continue
    tornati = set()
    degradato = False
    for it in (res or []):
        if isinstance(it, dict):
            i = it.get("id")
            if str(it.get("ranking") or "") == "keyword":
                degradato = True
        else:
            i = getattr(it, "id", None)
        if i:
            tornati.add(i)
    if degradato:
        degradate += 1
    n = len(ids & tornati)
    trovati += n
    attesi += len(ids)
    segno = "  " if n == len(ids) else ("~ " if n else "! ")
    print("%s %-38s %5d/%-2d  %s"
          % (segno, q[:38], n, len(ids), "DEGRADATA" if degradato else ""))

print("\n>>> miei fatti ritrovati entro k=%d: %d su %d = %.1f%%"
      % (K, trovati, attesi, 100.0 * trovati / max(1, attesi)))
print("    query dal TOPIC (caso onesto), corse degradate: %d su %d"
      % (degradate, len(per_topic)))
