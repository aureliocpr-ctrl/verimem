"""La prova ESEGUITA per le prime righe della mappa di client.py: il quickstart
del README (righe 428-442) su uno store temporaneo, senza toccare quello di
Aurelio. Stampa cosa fa davvero add() sui due casi che il README promette
(entailed -> admitted, confab -> QUARANTINED) e cosa torna search()."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = tempfile.mkdtemp(prefix="ws3-mappa-")
os.environ["ENGRAM_DATA_DIR"] = tmp
os.environ["VERIMEM_DATA_DIR"] = tmp
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
import verimem  # noqa: E402
from verimem import Memory  # noqa: E402

print("IMPORT DA", verimem.__file__)
print("STORE TEMPORANEO", tmp)
m = Memory(str(pathlib.Path(tmp) / "mappa.db"))
src = "Analytics runs on Postgres. The pipeline is nightly."
r1 = m.add("Analytics runs on Postgres.", source=src, topic="mappa/prova")
r2 = m.add("Analytics runs on MongoDB.", source=src, topic="mappa/prova")
for nome, r in (("entailed (README:441 -> admitted)", r1), ("confab (README:442 -> QUARANTINED)", r2)):
    print(f"\n{nome}")
    for k in ("stored", "id", "status", "grounding_score", "judged", "quarantined_by"):
        if isinstance(r, dict) and k in r:
            print(f"   {k} = {r[k]!r}")
    if isinstance(r, dict):
        w = r.get("warnings") or r.get("anti_confab_warnings") or []
        print(f"   layers = {[x.get('layer') for x in w if isinstance(x, dict)]}")
hits = m.search("Analytics", k=5)
print(f"\nsearch('Analytics', k=5) -> {len(hits)} hit")
for h in hits[:5]:
    d = h if isinstance(h, dict) else getattr(h, "__dict__", {})
    print(f"   status={d.get('status')!r} score={d.get('grounding_score')!r} «{str(d.get('proposition') or d.get('text'))[:60]}»")
print("\nrecall e search sono lo stesso oggetto?", Memory.recall is Memory.search if hasattr(Memory, "recall") else "Memory.recall NON esiste")
