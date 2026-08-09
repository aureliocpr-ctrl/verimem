import sys, os, sqlite3, json
sys.path.insert(0, "C:/Users/aurel/Code/HippoAgent")
os.environ.setdefault("ENGRAM_DATA_DIR", "C:/Users/aurel/.engram")
con = sqlite3.connect("file:C:/Users/aurel/.engram/semantic/semantic.db?mode=ro", uri=True)
quar = {r[0]: (r[1], r[2]) for r in con.execute(
    "SELECT id, grounding_score, substr(proposition,1,58) FROM facts WHERE status='quarantined'")}
con.close()
from verimem import Memory
from verimem.briefing import get_briefing
m = Memory()
print("MARK n_facts   quarantinati nel briefing")
primo = None
for n in (8, 10, 12, 16, 20, 30, 40):
    b = get_briefing(agent=m, n_facts=n)
    blob = json.dumps(b, default=str)
    c = [q for q in quar if q in blob]
    print("MARK   " + str(n).rjust(3) + "        " + str(len(c)).rjust(3) + ("   <-- primo" if c and primo is None else ""))
    if c and primo is None: primo = (n, c)
if primo:
    print("MARK")
    print("MARK === i quarantinati serviti dal briefing a n_facts=" + str(primo[0]) + " ===")
    for q in primo[1][:6]:
        gs, txt = quar[q]
        print("MARK   " + q + "  gs=" + str(round(gs,2) if gs is not None else "NULL").ljust(8) + str(txt)[:52])
