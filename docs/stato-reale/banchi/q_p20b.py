import sys, os, sqlite3, json
sys.path.insert(0, "C:/Users/aurel/Code/HippoAgent")
os.environ.setdefault("ENGRAM_DATA_DIR", "C:/Users/aurel/.engram")
con = sqlite3.connect("file:C:/Users/aurel/.engram/semantic/semantic.db?mode=ro", uri=True)
b = con.execute("SELECT id, proposition, grounding_score FROM facts WHERE status='quarantined' "
                "AND superseded_by IS NULL ORDER BY created_at DESC LIMIT 1").fetchone()
con.close()
fid, testo, gs = b
print("MARK bersaglio " + fid + "  gs=" + str(gs)[:6])
print("MARK testo: " + testo[:90])
q = " ".join(testo.split()[:6])
print("MARK query:  " + q)
print("MARK")
from verimem import Memory
m = Memory()
def ids_di(r):
    out = []
    for x in (r if isinstance(r, (list, tuple)) else [r]):
        if isinstance(x, dict): out.append(str(x.get("id") or x.get("fact_id")))
        else: out.append(str(getattr(x, "id", getattr(x, "fact_id", ""))))
    return out
print("MARK === LE PORTE PER QUERY (dove l'utente NON sa cosa c'e' dentro) ===")
for nome, fn in (("search", lambda: m.search(q, k=20)),
                 ("recall", lambda: m.recall(q, k=20)),
                 ("ask",    lambda: m.ask(q, k=20)),
                 ("answer", lambda: m.answer(q)),
                 ("explain",lambda: m.explain(q, k=20))):
    try:
        r = fn()
        blob = json.dumps(r, default=str)[:4000] if not isinstance(r, (list, tuple)) else json.dumps(ids_di(r), default=str)
        c = len(r) if isinstance(r, (list, tuple)) else 1
        print("MARK   " + nome.ljust(9) + "n=" + str(c).ljust(5) +
              ("** CONTIENE IL QUARANTINATO **" if fid in blob else "no"))
    except Exception as e:
        print("MARK   " + nome.ljust(9) + "ERR " + type(e).__name__ + ": " + str(e)[:70])
