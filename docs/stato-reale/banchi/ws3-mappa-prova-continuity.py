"""`continuity.py` (19): la CATENA — il lineage dei fatti, i checkpoint, gli
handoff, la riparazione dei collegamenti.

⛔ Tutto su uno store TEMPORANEO mio: `save_checkpoint` e `handoff_prepare`
scrivono davvero, e lo store di Aurelio non si tocca.

I due punti che decidono:
  · `resolve_prefix` promette «>= 6 caratteri» e un id UNICO: si prova col
    prefisso corto (deve rifiutare), con uno ambiguo (deve rifiutare) e con uno
    buono (deve risolvere);
  · `walk_forward` promette di riconoscere «tutte e quattro le codifiche
    dell'appartenenza nella colonna separata da virgole»: le costruisco tutte e
    quattro e guardo quali trova.
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import sys
import tempfile
import time

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-cont-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402
from verimem import continuity as CT  # noqa: E402

m = Memory(str(tmp / "c.db"))
sm = m.semantic
F = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
a = m.add("Il canone del capannone 12 e' 5900 euro.", source=F, topic="project/verimem/uno")
b = m.add("Il capannone 12 e' in via Roma.", source="Il capannone 12 e' in via Roma.",
          topic="project/verimem/due")
ida, idb = a.get("id"), b.get("id")
print("due fatti:", ida, idb)

print("\n=== _parse_ids: la colonna separata da virgole, coi vuoti di legacy")
for grezzo in ("aaa,bbb", "aaa,,bbb", "", None, ",", "  aaa , bbb "):
    print(f"  {grezzo!r:16} -> {CT._parse_ids(grezzo)}")

print("\n=== resolve_prefix: corto, ambiguo, buono")
for p in (ida[:3], ida[:6], ida, "zzzzzzzz"):
    try:
        print(f"  {p!r:16} -> {CT.resolve_prefix(sm, p)}")
    except Exception as e:  # noqa: BLE001
        print(f"  {p!r:16} -> {type(e).__name__}: {str(e)[:70]}")

print("\n=== tip_fact / recent_facts")
tip = CT.tip_fact(sm)
print("  tip_fact:", (tip or {}).get("id") if isinstance(tip, dict) else tip)
rec = CT.recent_facts(sm, 5, False)
print("  recent_facts(5):", len(rec), "nodi ·", [str(x.get('id'))[:12] for x in rec])

print("\n=== resolve_lineage: auto | topic | latest | prefisso")
for ref in ("auto", "latest", "topic", ida[:8], "riferimento-inventato"):
    try:
        print(f"  {ref!r:24} -> {CT.resolve_lineage(sm, ref, 'project/verimem/tre')}")
    except Exception as e:  # noqa: BLE001
        print(f"  {ref!r:24} -> {type(e).__name__}: {str(e)[:80]}")

print("\n=== save_checkpoint: scrive ATTRAVERSO il gate, incatenato")
ck = CT.save_checkpoint(m, "Ho chiuso la mappa di client.py.",
                        topic="project/verimem/mappa", lineage_to=ida)
print("  ricevuta:", {k: str(v)[:44] for k, v in list(ck.items())[:6]})
idck = ck.get("id")

print("\n=== walk_backward / walk_forward")
indietro = CT.walk_backward(sm, idck, 10)
print("  walk_backward dal checkpoint:", [str(n.get('id'))[:12] for n in indietro])
avanti = CT.walk_forward(sm, ida, 10)
print("  walk_forward dal primo fatto:", [str(n.get('id'))[:12] for n in avanti])

print("\n  le QUATTRO codifiche dell'appartenenza, costruite a mano nel db:")
forme = {"esatta": ida,
         "testa": f"{ida},xxxx",
         "coda": f"xxxx,{ida}",
         "mezzo": f"xxxx,{ida},yyyy"}
# PRIMA tutte le scritture (ogni `add` apre la sua connessione), POI gli UPDATE
# su una connessione mia: tenerne una aperta mentre `add` scrive dà
# «database is locked» dopo 65 s di attesa — lezione del giro precedente.
creati = {}
for nome in forme:
    nuovo = m.add(f"Fatto figlio con codifica {nome} del capannone 12.",
                  source=f"Fatto figlio con codifica {nome} del capannone 12.",
                  topic="project/verimem/figli")
    creati[nome] = nuovo.get("id")
con = sqlite3.connect(str(sm.db_path))
print("   fatti nel db:", con.execute("SELECT COUNT(*) FROM facts").fetchone()[0])
for nome, valore in forme.items():
    con.execute("UPDATE facts SET lineage_to = ? WHERE id = ?", (valore, creati[nome]))
con.commit()
con.close()
trovati = CT.walk_forward(sm, ida, 10)
ids_trovati = {str(n.get("id")) for n in trovati}
for nome, fid in creati.items():
    print(f"   codifica {nome:8} ({fid[:12]}) trovata da walk_forward:", fid in ids_trovati)

print("\n=== find_orphans / since_epoch")
for spec in ("today", "2h", "3d", "1w", "5m", "spazzatura"):
    try:
        print(f"  since_epoch({spec!r:12}) -> {CT.since_epoch(spec)}")
    except Exception as e:  # noqa: BLE001
        print(f"  since_epoch({spec!r:12}) -> {type(e).__name__}: {str(e)[:60]}")
# `find_orphans` rende un DICT {"orphans": [...], "total": N}, non una tupla:
# spacchettarlo in due nomi dava le CHIAVI, e `len("orphans")` = 7 stampava
# «7 orfani» — un numero plausibile che non era il numero. Errore mio, tenuto
# scritto perché è la forma che inganna di più.
rapporto = CT.find_orphans(sm, time.time() - 3600, 50)
print("  find_orphans nell'ultima ora:", len(rapporto["orphans"]), "orfani su",
      rapporto["total"], "fatti nella finestra · chiavi:", sorted(rapporto))

print("\n=== relink: la riparazione della catena")
print("  prima:", CT.walk_backward(sm, creati["esatta"], 5))
r = CT.relink(sm, creati["esatta"], idb, False)
print("  relink(figlio -> secondo fatto) ->", str(r)[:110])
print("  dopo:", [str(n.get('id'))[:12] for n in CT.walk_backward(sm, creati["esatta"], 5)])

print("\n=== handoff_prepare / handoff_show / handoff_log")
h = CT.handoff_prepare(m, "Consegna: la mappa di gateway.py e' a meta'.", label="ws3")
print("  handoff_prepare:", {k: str(v)[:40] for k, v in list(h.items())[:5]})
print("  handoff_show('ws3'):", str(CT.handoff_show(sm, "ws3"))[:110])
print("  handoff_show('nessuno'):", CT.handoff_show(sm, "etichetta-inesistente"))
print("  handoff_log('ws3', 5):", len(CT.handoff_log(sm, "ws3", 5)), "voci")

print("\n=== collect_digest: il racconto della finestra")
d = CT.collect_digest(sm, 24)
if isinstance(d, dict):
    for k, v in d.items():
        print(f"  {k}: {str(v)[:150]}")
else:
    print(" ", str(d)[:300])

print("\n=== _node / _namespace (le due private di supporto)")
# `_node` legge la riga per POSIZIONE (row[0]…row[8]) e l'ordine è quello di
# `_NODE_COLS`: con un `SELECT *` i campi escono sfasati (topic col testo,
# created_at con la confidence). Non è un difetto — è la query sbagliata mia.
con = sqlite3.connect(str(sm.db_path))
riga_giusta = con.execute(
    f"SELECT {CT._NODE_COLS} FROM facts LIMIT 1").fetchone()
riga_sbagliata = con.execute("SELECT * FROM facts LIMIT 1").fetchone()
con.close()
print("  _node(riga con _NODE_COLS):",
      {k: str(v)[:34] for k, v in list(CT._node(riga_giusta).items())[:5]})
print("  _node(riga da SELECT *)   :",
      {k: str(v)[:34] for k, v in list(CT._node(riga_sbagliata).items())[:5]})
for t, dep in (("project/verimem/uno", 1), ("project/verimem/uno", 2), ("senza", 1)):
    print(f"  _namespace({t!r}, {dep}) -> {CT._namespace(t, dep)!r}")
