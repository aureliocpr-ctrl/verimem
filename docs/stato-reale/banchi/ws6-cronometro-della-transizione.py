"""Coglie la transizione del pavimento MENTRE avviene, e ne misura il costo.

client.py:1271 chiama _auto_relevance_floor() dentro un try NON condizionato:
ogni recall passa di li'. La cache in-processo dura 300 s, ma ogni banco e' un
processo nuovo, quindi legge sempre il file. Finche' la deriva del conteggio
resta sotto _FLOOR_DRIFT (5%) il file viene servito; appena la supera, la
PRIMA recall ricalcola - e paga.

⚠️ Non sono un osservatore neutrale: eseguendo questo banco POTREI essere io a
innescare il ricalcolo. Lo dichiaro invece di presentarmi come spettatore.

Misura, in una sola esecuzione:
  - floor.json prima (mtime + contenuto)
  - il tempo di UNA recall attraverso la porta alta
  - floor.json dopo
  - il verdetto sulle tre predizioni registrate nel doc 53

SOLA LETTURA sullo store (la recall e' una lettura). Nessun rm, nessuna
scrittura mia: se il file cambia, l'ha riscritto il PRODOTTO.
"""
import json
import os
import sqlite3
import time

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
FLOOR = DB + ".floor.json"
MTIME_ORIGINALE = "2026-08-30 20:32:08"
BANDA = (0.87, 0.89)          # P3, registrata nel doc 53
SOGLIA_ATTESA = 14485         # P2


def leggi_floor():
    try:
        with open(FLOOR, encoding="utf-8") as fh:
            d = json.load(fh)
        return d, time.strftime("%Y-%m-%d %H:%M:%S",
                                time.localtime(os.path.getmtime(FLOOR)))
    except Exception as e:      # noqa: BLE001 - il file puo' non esistere
        return {"errore": str(e)}, None


prima, mtime_prima = leggi_floor()
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
vivi = con.execute(
    "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL").fetchone()[0]
con.close()

salvato = int(prima.get("n_facts") or 0)
tolleranza = max(1, salvato) * 0.05
margine = int(tolleranza - abs(vivi - salvato))
print("fatti vivi ora      : %d" % vivi)
print("floor.json PRIMA    : %s   mtime %s" % (json.dumps(prima), mtime_prima))
print("margine residuo     : %d" % margine)

from verimem.client import Memory   # noqa: E402 - dopo la lettura del file

t0 = time.time()
m = Memory(DB)
t_costruzione = time.time() - t0

t0 = time.time()
res = m.recall("il pavimento di rilevanza dello store", k=5)
t_recall = time.time() - t0

dopo, mtime_dopo = leggi_floor()
print("floor.json DOPO     : %s   mtime %s" % (json.dumps(dopo), mtime_dopo))
print("costruzione Memory  : %6.2f s" % t_costruzione)
print("UNA recall          : %6.2f s   <-- e' il tempo che paga chi chiede"
      % t_recall)

avviso = None
try:
    avviso = getattr(res, "sotto_il_pavimento", None)
except Exception:               # noqa: BLE001
    pass
print("campo sotto_il_pavimento: %s" % (avviso if avviso else "assente"))

cambiato = (mtime_dopo or "") [:19] != MTIME_ORIGINALE
print("\nLE TRE PREDIZIONI DEL DOC 53")
p1 = "SCATTATA" if cambiato else "non ancora (mtime invariato)"
print("  P1 il file viene RISCRITTO                : %s" % p1)
if not cambiato:
    print("  P2, P3: non valutabili finche' P1 non scatta.")
else:
    n = int(dopo.get("n_facts") or 0)
    f = float(dopo.get("floor") or 0.0)
    print("  P2 n_facts >= %d                       : %s (n_facts=%d)"
          % (SOGLIA_ATTESA, "REGGE" if n >= SOGLIA_ATTESA else "CADE", n))
    dentro = BANDA[0] <= f <= BANDA[1]
    print("  P3 floor fra %.2f e %.2f                 : %s (floor=%.4f)"
          % (BANDA[0], BANDA[1], "REGGE" if dentro else "CADE", f))
    if not dentro:
        print("     ^^ P3 CADUTA: la mia lettura del meccanismo e' sbagliata "
              "e va detto, non aggiustato dopo.")
