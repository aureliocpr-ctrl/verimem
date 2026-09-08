"""Le 17 definizioni che il CONTATORE DELLO SCRIPT dice mancanti in client.md —
il mio conteggio a memoria diceva 6, ed era sbagliato per eccesso.

La prima domanda è quella che può ridimensionare il MIO candidato P0: il
docstring di `undo` dice che la maniglia arriva in `update()['undo_op_id']` e
che «il ping-pong finisce con ENTRAMBI i fatti». Se `undo` recupera il fatto che
T-MAP-8 fa sparire, la cura esiste già e il ticket cambia peso. Lo misuro io per
primo, prima che lo faccia qualcun altro.
"""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-u17-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
os.environ["VERIMEM_AUDIT_LOG"] = "1"          # per far nascere adjudications.db
from verimem import Memory  # noqa: E402
from verimem import client as C  # noqa: E402

FONTE = ("Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro "
         "e la consegna e' prevista per il 3 marzo.")


def servite(m, q="canone capannone 12"):
    return [str(h.get("text"))[:46] for h in m.search(q, k=10)]


print("=== 1. `undo` RIPARA il buco di T-MAP-8? (il controllo contro il mio ticket)")
d = pathlib.Path(tempfile.mkdtemp(prefix="ws3-u17-"))
m = Memory(str(d / "u.db"))
r = m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="u/x")
print("  search prima:", servite(m))
u = m.update(r["id"], "Il canone del capannone 12 e' 6100 euro.", topic="u/x")
print("  update -> status:", u.get("status"), "| chiavi della ricevuta:", sorted(u))
op = u.get("undo_op_id") or (u.get("superseded_undo_ops") or [None])[0]
print("  maniglia undo trovata nella ricevuta:", op)
print("  search dopo update:", servite(m))
if op:
    res = m.undo(op)
    print("  undo(op) ->", {k: str(v)[:60] for k, v in list(res.items())[:6]})
    print("  search DOPO undo:", servite(m))
    print("  >>> il fatto vero e' tornato:", len(servite(m)) > 0)
else:
    print("  >>> NESSUNA MANIGLIA nella ricevuta di update: l'utente non ha")
    print("      il modo di annullare, se non passando dal retirement_log")
    rl = m.retirement_log(limit=3)
    print("      retirement_log[0] undo_op_id:",
          (rl[0].get("undo_op_id") if rl else None))
    if rl and rl[0].get("undo_op_id"):
        res = m.undo(rl[0]["undo_op_id"])
        print("      undo dalla riga del registro ->", str(res)[:90])
        print("      search DOPO undo:", servite(m))

print("\n=== 2. audit_anchor / audit_verify_anchor (la ricevuta FIRMATA)")
m2 = Memory(str(d / "a.db"))
m2.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="a/x")
try:
    anc = m2.audit_anchor()
    print("  audit_anchor ->", {k: str(v)[:52] for k, v in list(anc.items())[:8]})
    ver = m2.audit_verify_anchor(anc)
    print("  audit_verify_anchor(receipt) ->", ver)
    anc2 = dict(anc)
    for campo in ("mutations_head", "head", "adjudications_head"):
        if campo in anc2:
            anc2[campo] = "0" * 32
            break
    print("  con una testa MANOMESSA ->", m2.audit_verify_anchor(anc2))
except Exception as e:  # noqa: BLE001
    print("  ECCEZIONE:", type(e).__name__, str(e)[:150])

print("\n=== 3. record_decision / decision_outcome / why_decision")
dec = m2.record_decision("uso Postgres per l'analytics", topic="a/dec")
did = dec.get("id") if isinstance(dec, dict) else dec
print("  record_decision ->", str(dec)[:100])
try:
    print("  decision_outcome(senza verified_by) ->", end=" ")
    print(m2.decision_outcome(did, "ha retto il carico di marzo"))
except Exception as e:  # noqa: BLE001
    print(type(e).__name__, str(e)[:90])
try:
    print("  decision_outcome(con verified_by) ->",
          m2.decision_outcome(did, "ha retto il carico di marzo",
                              verified_by=["file:report-marzo.md"]))
except Exception as e:  # noqa: BLE001
    print("  ECCEZIONE:", type(e).__name__, str(e)[:110])
print("  why_decision('Postgres') ->", str(m2.why_decision("Postgres"))[:150])

print("\n=== 4. i lazy sibling: _decisions, _adjudication_log, _floor_file")
for nome in ("decisions.db", "adjudications.db"):
    p = pathlib.Path(str(m2.semantic.db_path)).parent / nome
    print(f"  {nome:20} esiste dopo le scritture:", p.exists())
print("  _floor_file ->", pathlib.Path(str(m2._floor_file())).name,
      "| esiste:", pathlib.Path(str(m2._floor_file())).exists())
print("  _auto_relevance_floor() ->", m2._auto_relevance_floor())
print("  _floor_file esiste dopo la stima:", pathlib.Path(str(m2._floor_file())).exists())

print("\n=== 5. _esiste_gia_identico (uguaglianza esatta, non similarita')")
print("  identico stesso topic  :",
      C._esiste_gia_identico(m2.semantic, "Il canone del capannone 12 e' 5900 euro.", "a/x"))
print("  identico altro topic   :",
      C._esiste_gia_identico(m2.semantic, "Il canone del capannone 12 e' 5900 euro.", "a/zzz"))
print("  simile ma non identico :",
      C._esiste_gia_identico(m2.semantic, "Il canone del capannone 12 e 5900 euro", "a/x"))

print("\n=== 6. _fact_view: la STESSA superficie di provenienza ovunque")
uno = m2.get_all(limit=1)
print("  campi di get_all()[0]:", sorted(uno[0]) if uno else None)
hit = m2.search("canone", k=1)
print("  campi di search()[0] :", sorted(hit[0]) if hit else None)
if uno and hit:
    solo_get = set(uno[0]) - set(hit[0])
    solo_search = set(hit[0]) - set(uno[0])
    print("  solo in get_all:", sorted(solo_get), "| solo in search:", sorted(solo_search))

print("\n=== 7. _spiega_le_quarantene (via quarantine_log(explain=True))")
m2.add("Il canone del capannone 12 e' 9999 euro.", source=FONTE, topic="a/ko")
ql = m2.quarantine_log(limit=5, explain=True)
print("  righe:", len(ql), "| chiavi della prima:", sorted(ql[0]) if ql else None)
if ql:
    for k in ("reason", "advice", "come_sbloccarlo", "unblock", "spiegazione"):
        if k in ql[0]:
            print(f"  {k}: {str(ql[0][k])[:120]}")

print("\n=== 8. _content_pins (le ricevute legate al CONTENUTO)")
f = d / "contratto.txt"
f.write_text("Il canone del capannone 12 e' 5900 euro.\n", encoding="utf-8")
print(f"  _content_pins(['file:{f.name}'])", "->",
      {k: str(v)[:24] for k, v in m2._content_pins([f"file:{f}"]).items()})
print("  _content_pins(['file:/non/esiste']) ->", m2._content_pins(["file:/non/esiste"]))

print("\n=== 9. persisti_chi_ha_quarantinato e _remote_cls")
righe = m2.quarantine_log(limit=1)
if righe:
    fid = righe[0].get("id")
    print("  persisti(db, id, 'L1') ->",
          C.persisti_chi_ha_quarantinato(m2.semantic.db_path, fid, "L1"))
    print("  chi_ha_quarantinato ora nel fatto:",
          (m2.get(fid) or {}).get("quarantined_by"))
print("  _remote_cls() ->", C._remote_cls().__name__)
