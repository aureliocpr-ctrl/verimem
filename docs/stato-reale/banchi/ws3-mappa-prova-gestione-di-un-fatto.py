"""Blocco 11 della mappa di client.py: i metodi PUBBLICI di lettura e gestione
di un fatto — quelli che un utente dell'SDK chiama dopo aver scritto.

Il pezzo che serve anche a @ws5 (T49, «sei tool servono i quarantinati alla
porta»): in client.py `list_facts` ha DUE chiamanti (3550 `epistemic_health`,
3962 `get_all`) e `hide_low_trust` **non compare mai** nel file. Il default del
parametro è `False`, quindi entrambe vedono i quarantinati. Su
`epistemic_health` è voluto (misura la salute del corpus intero); su `get_all`
il docstring promette solo «List stored facts (with provenance), newest-relevant
first. mem0/Zep parity» e non dice che include i bloccati. Qui lo misuro alla
PORTA, non lo deduco dalla lettura.

Le firme sono state LETTE prima di chiamare (lezione del turno precedente: 5
TypeError su 6 per aver chiamato a intuito).
"""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-gest-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402

F = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
m = Memory(str(tmp / "g.db"))
buono = m.add("Il canone del capannone 12 e' 5900 euro.", source=F, topic="g/ok")
cattivo = m.add("Il canone del capannone 12 e' 7300 euro.", source=F, topic="g/ko")
id_b, id_c = buono.get("id"), cattivo.get("id")
print("scritture:", buono.get("status"), "|", cattivo.get("status"))

print("\n=== T49 ALLA PORTA: get_all() serve i quarantinati?")
tutti = m.get_all(limit=100)
stati = {}
for f in tutti:
    stati[f.get("status")] = stati.get(f.get("status"), 0) + 1
print("  get_all() -> n =", len(tutti), "| per status:", stati)
print("  >>> il quarantinato compare in get_all():",
      any(f.get("id") == id_c for f in tutti))
print("  per confronto, search('canone capannone') ->",
      len(m.search("canone capannone", k=10)), "risultati serviti")
print("  e get_all(topic='g/ko') ->", len(m.get_all(topic="g/ko")))

print("\n=== get / history / update: il fatto e la sua catena")
g = m.get(id_b)
print("  get(id) chiavi:", sorted(g)[:12] if g else None)
print("  get('id-inesistente'):", m.get("0" * 16))
u = m.update(id_b, "Il canone del capannone 12 e' 6100 euro.", topic="g/ok")
print("  update -> stored:", u.get("stored"), "| status:", u.get("status"),
      "| supersedes:", str(u.get("supersedes"))[:40])
h = m.history(id_b)
print("  history(id vecchio) -> catena di", len(h), "->",
      [(x.get("status"), str(x.get("text"))[:34]) for x in h])
if u.get("id"):
    h2 = m.history(u["id"])
    print("  history(id nuovo)  -> stessa catena?", len(h2) == len(h))

print("\n=== quarantine_log / restore / label")
ql = m.quarantine_log(limit=10)
print("  quarantine_log ->", len(ql), "righe · prima:",
      {k: str(v)[:48] for k, v in list(ql[0].items())[:5]} if ql else None)
print("  restore(id_quarantinato) ->", m.restore(id_c, reason="falso positivo di prova"))
print("  status dopo restore:", (m.get(id_c) or {}).get("status"))
print("  ora search lo serve?",
      any(str(x.get("text", "")).find("7300") >= 0
          for x in m.search("canone capannone", k=10)))
print("  label(id,'proven',proof=…) ->",
      m.label(id_b, "proven", proof="tests/test_x.py::test_y"))
print("  label(id,'inventato') ->", end=" ")
try:
    print(m.label(id_b, "inventato"))
except Exception as e:  # noqa: BLE001
    print(type(e).__name__, str(e)[:80])

print("\n=== i registri: retirement_log, verdict_mismatches, survivability, tier_inventory")
rl = m.retirement_log(limit=5, with_text=True)
print("  retirement_log ->", len(rl), "righe ·",
      {k: str(v)[:40] for k, v in list(rl[0].items())[:6]} if rl else "vuoto")
vm = m.verdict_mismatches(limit=5)
print("  verdict_mismatches -> chiavi:", sorted(vm) if isinstance(vm, dict) else vm)
sv = m.survivability()
print("  survivability ->", sv)
ti = m.tier_inventory()
print("  tier_inventory -> chiavi:", sorted(ti)[:8] if isinstance(ti, dict) else ti)

print("\n=== epistemic_health e ignorance")
eh = m.epistemic_health(limit=50)
print("  epistemic_health -> chiavi:", sorted(eh) if isinstance(eh, dict) else eh)
ig = m.ignorance(["quanto costa il capannone 99?"], k=3)
print("  ignorance -> chiavi:", sorted(ig) if isinstance(ig, dict) else ig)
print("  ignorance (prima voce):",
      str(list(ig.values())[0])[:200] if isinstance(ig, dict) and ig else "-")

print("\n=== forget_with_report e delete: dove il fatto resta leggibile")
fw = m.forget_with_report(id_b)
print("  forget_with_report ->", {k: str(v)[:70] for k, v in list(fw.items())[:6]})
print("  get dopo forget:", m.get(id_b))
print("  delete(id_quarantinato) ->", m.delete(id_c))
print("  get_all dopo le due cancellazioni ->", len(m.get_all(limit=100)))
