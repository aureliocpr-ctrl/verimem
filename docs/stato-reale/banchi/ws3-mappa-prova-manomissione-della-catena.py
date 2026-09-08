"""Il controllo che DISTINGUE, per la riga `audit_verify` della mappa: torna
None quando la catena è intatta — ma torna anche None quando l'audit non è mai
stato acceso. Un valore che non separa i due casi non prova niente, quindi qui
la catena si MANOMETTE e si guarda se il segnale si accende.

E si rifà `why_decision` con una DOMANDA (il docstring dice «Why did we choose
X?»), non con l'id: la prova precedente l'aveva chiamata male."""
import os
import pathlib
import sqlite3
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-manom-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ["VERIMEM_AUDIT_LOG"] = "1"
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402

FONTE = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
m = Memory(str(tmp / "m.db"))
m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="a/1")
m.add("Il canone del capannone 12 e' 7300 euro.", source=FONTE, topic="a/2")
m.add("La consegna e' del 3 marzo.", source=FONTE, topic="a/3")

print("PRIMA della manomissione:")
print("   audit_verify():", m.audit_verify(), " (None = catena intatta)")
print("   audit_head()  :", str(m.audit_head())[:24], "…")
print("   righe nel log :", len(m.audit_log()))

# dove vive il db dell'audit
cand = list(tmp.rglob("*.db")) + list(tmp.rglob("*.sqlite*"))
print("\n   file db sotto lo store:", [p.name for p in cand])
audit_db = next((p for p in cand if "adjud" in p.name.lower() or "audit" in p.name.lower()), None)
if audit_db is None:
    audit_db = next((p for p in cand if p.name != "m.db"), None)
print("   db dell'audit scelto:", audit_db.name if audit_db else "NON TROVATO")

if audit_db is not None:
    con = sqlite3.connect(str(audit_db))
    tabelle = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print("   tabelle:", tabelle)
    tab = next((t for t in tabelle if "adjud" in t or "audit" in t or "log" in t), tabelle[0] if tabelle else None)
    if tab:
        righe = con.execute(f"SELECT * FROM {tab} LIMIT 3").fetchall()  # noqa: S608
        cols = [d[0] for d in con.execute(f"SELECT * FROM {tab} LIMIT 1").description]  # noqa: S608
        print(f"   tabella {tab}: {len(righe)} righe lette, colonne {cols[:10]}")
        # MANOMISSIONE: cambio la proposition della PRIMA riga (una modifica interna)
        pid = righe[0][cols.index("id")] if "id" in cols else None
        if pid is not None and "proposition" in cols:
            con.execute(f"UPDATE {tab} SET proposition = ? WHERE id = ?",  # noqa: S608
                        ("MANOMESSO: il canone e' 1 euro.", pid))
            con.commit()
            print(f"   manomessa la riga id={pid}")
    con.close()

print("\nDOPO la manomissione (nuovo handle, per non leggere una cache):")
m2 = Memory(str(tmp / "m.db"))
print("   audit_verify():", m2.audit_verify(), " (un id = prima riga manomessa)")
print("   audit_head()  :", str(m2.audit_head())[:24], "…")

print("\n--- why_decision con una DOMANDA (non con l'id: prima l'avevo chiamata male)")
d = m2.record_decision("uso Postgres per l'analytics", topic="dec/db")
print("   record_decision ->", str(d)[:60])
for domanda in ("Why did we choose Postgres?", "perche' Postgres", "Postgres"):
    try:
        r = m2.why_decision(domanda)
        print(f"   why_decision({domanda!r}) -> {len(r)} decisioni {[x.get('decision') for x in r][:2]}")
    except Exception as e:  # noqa: BLE001
        print(f"   why_decision({domanda!r}) -> ECCEZIONE {type(e).__name__} {str(e)[:80]}")
